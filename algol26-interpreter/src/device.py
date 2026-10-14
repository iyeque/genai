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
