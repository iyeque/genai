"""Device abstraction for Phase 5.2 (hardware-acceleration primitives).

This module defines the uniform device-array interface that @kernel procs run
against. The active backend is a *CPU reference backend*: it executes the
kernel body elementwise over a Python list, producing real numeric results.

A future GPU backend (CUDA/OpenCL) slots in behind the same interface without
touching the language surface: DeviceArray carries the data plus a device tag,
and `launch` dispatches to whichever backend is registered for that tag. On a
machine with no GPU, the CPU backend is always the fallback, so programs are
verifiable everywhere.

Honest scope note: the GPU backend is intentionally not implemented here — this
box has no GPU/CUDA to validate against, and shipping an unverifiable codegen
path would be a fabrication. The CPU reference backend proves the language
design and gives a tested, extensible compute model; GPU is a backend swap.
"""


class DeviceArray:
    """An array tagged with the device it lives on.

    `data` is a plain Python list of numbers (the CPU reference backend's
    storage). `device` is the tag from the kernel attribute (e.g. 'gpu',
    'cpu'); on this build every device tag is served by the CPU backend.
    """

    def __init__(self, data, device="cpu"):
        self.data = list(data)
        self.device = device

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def __repr__(self):
        return f"DeviceArray({self.data!r}, device={self.device!r})"


class CPUReferenceBackend:
    """Reference backend: maps a scalar kernel over each element of an array.

    The kernel is invoked once per element with the element bound to the
    kernel's single scalar parameter, and the per-element return values are
    collected into a new DeviceArray. This is a faithful, if unoptimized,
    execution of the elementwise semantics a real GPU kernel would provide.
    """

    name = "cpu"

    def launch(self, kernel_fn, device_array):
        """Apply `kernel_fn` (a callable taking one scalar) over the array."""
        if not isinstance(device_array, DeviceArray):
            raise TypeError("launch() expects a device array (use to_device)")
        out = [kernel_fn(x) for x in device_array.data]
        return DeviceArray(out, device=self.name)


# The single registered backend. GPU would register here when available.
_ACTIVE_BACKEND = CPUReferenceBackend()


def active_backend():
    return _ACTIVE_BACKEND


def to_device(data, device="gpu"):
    """Move a host array onto a device, returning a DeviceArray.

    `device` names the target (e.g. 'gpu'); on this build it is served by the
    CPU reference backend. Accepts a plain list of numbers.
    """
    if isinstance(data, DeviceArray):
        # Already on a device; re-tag to the requested device.
        return DeviceArray(data.data, device=device)
    if not isinstance(data, (list, tuple)):
        raise TypeError("to_device() expects an array (list of numbers)")
    return DeviceArray(list(data), device=device)


def from_device(device_array):
    """Move a device array back to the host as a plain list."""
    if isinstance(device_array, DeviceArray):
        return list(device_array.data)
    if isinstance(device_array, (list, tuple)):
        return list(device_array)
    raise TypeError("from_device() expects a device array")


def launch(kernel_fn, device_array):
    """Run a kernel over a device array on the active backend."""
    return _ACTIVE_BACKEND.launch(kernel_fn, device_array)


# ---------------------------------------------------------------------------
# Heterogeneous compute graph (Phase 5.2)
#
# A ComputeGraph records a DAG of device operations (host->device transfers and
# kernel launches) as *lazy* nodes. Nothing executes until materialize() is
# called on a node, which walks the dependency chain and runs each op on the
# active backend. The point is data-movement minimization: an intermediate
# node that is only ever consumed by another device op stays a DeviceArray on
# the backend and is never copied back to host — only the final materialize()
# crosses the host boundary once.
# ---------------------------------------------------------------------------

class _GraphNode:
    """A lazy node in a ComputeGraph.

    kind:
      'host'    — a host-side value (list); .value holds it.
      'transfer'— host -> device; .src is a node, .device the target tag.
      'launch'  — kernel over a device node; .kernel is the callable, .src
                  the input device node.
    """
    __slots__ = ("kind", "value", "src", "kernel", "device", "graph")

    def __init__(self, kind, graph, value=None, src=None, kernel=None, device=None):
        self.kind = kind
        self.graph = graph
        self.value = value
        self.src = src
        self.kernel = kernel
        self.device = device


class ComputeGraph:
    """Records device ops and materializes results with minimal data movement.

    Nodes are produced by transfer()/launch() and are lazy; the backend runs
    them only when materialize() is requested. Execution is memoized per node
    so shared subexpressions run once.
    """

    def __init__(self, backend=None):
        self.backend = backend or _ACTIVE_BACKEND
        self._cache = {}   # id(node) -> computed DeviceArray (or host list)
        self._node_seq = 0

    def _new_node(self, kind, **kw):
        self._node_seq += 1
        return _GraphNode(kind, self, **kw)

    def host(self, value):
        """Wrap a host-side list as a graph node (no device movement)."""
        if not isinstance(value, (list, tuple)):
            raise TypeError("graph host value must be an array (list of numbers)")
        return self._new_node("host", value=list(value))

    def transfer(self, src, device="gpu"):
        """Record host -> device. `src` may be a raw list or a graph node."""
        if isinstance(src, _GraphNode):
            src_node = src
        else:
            src_node = self.host(src)
        return self._new_node("transfer", src=src_node, device=device)

    def launch(self, kernel_fn, src):
        """Record a kernel launch over a device node. Lazy; stays on-device."""
        if not isinstance(src, _GraphNode):
            raise TypeError("graph launch() input must be a graph node (use transfer)")
        return self._new_node("launch", src=src, kernel=kernel_fn)

    def _eval(self, node):
        """Compute a node's value as a DeviceArray (device-side), memoized."""
        key = id(node)
        if key in self._cache:
            return self._cache[key]
        if node.kind == "host":
            # A bare host list: treat as already-on-device storage for chaining.
            result = DeviceArray(node.value, device=self.backend.name)
        elif node.kind == "transfer":
            upstream = self._eval(node.src)
            data = upstream.data if isinstance(upstream, DeviceArray) else upstream
            result = DeviceArray(list(data), device=node.device)
        elif node.kind == "launch":
            upstream = self._eval(node.src)
            if not isinstance(upstream, DeviceArray):
                upstream = DeviceArray(list(upstream), device=self.backend.name)
            result = self.backend.launch(node.kernel, upstream)
        else:
            raise TypeError(f"unknown graph node kind {node.kind!r}")
        self._cache[key] = result
        return result

    def materialize(self, node):
        """Execute the chain up to `node` and return a host-side list.

        This is the single host boundary: intermediates consumed only by other
        device ops never leave the backend, so a fused pipeline pays the
        host<->device cost exactly once (here), not per stage.
        """
        if not isinstance(node, _GraphNode):
            raise TypeError("materialize() expects a graph node")
        device_value = self._eval(node)
        return list(device_value.data)


def graph():
    """Create a fresh compute graph."""
    return ComputeGraph()

