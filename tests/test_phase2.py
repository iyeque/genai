"""
Integration test for ALGOL 26 Phase 2 type system.
Tests: let-polymorphism, Hindley-Milner inference, basic type checking.
"""

from parser import parse
from typechecker import TypeChecker, TypeCheckError
from interpreter import Evaluator
import traceback


def test_simple_let_polymorphism():
    """Test: let x = 5 in x + 1 should infer x as int"""
    source = """
    module test
    {
      func main() = 
        let x = 5 in
        x + 1
    }
    """
    print("Test 1: Simple let-polymorphism")
    ast = parse(source)
    checker = TypeChecker()
    try:
        typed_ast = checker.check_module(ast)
        print("  ✓ Type checking succeeded")
        # Evaluate
        evaluator = Evaluator()
        result = evaluator.eval_module(typed_ast)
        print("  ✓ Evaluation succeeded")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False


def test_generic_identity():
    """Test: Identity function should be polymorphic"""
    source = """
    module test
    {
      func id[T](x: T) -> T = x
      func main() = 
        let x = id(5) in
        let y = id(true) in
        x
    }
    """
    print("\nTest 2: Generic identity function")
    ast = parse(source)
    checker = TypeChecker()
    try:
        typed_ast = checker.check_module(ast)
        print("  ✓ Type checking succeeded")
        evaluator = Evaluator()
        result = evaluator.eval_module(typed_ast)
        print("  ✓ Evaluation succeeded")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False


def test_let_polymorphism_in_action():
    """Test: Let-polymorphism with multiple uses of same function"""
    source = """
    module test
    {
      func compose[T, U, V](f: U -> V, g: T -> U) -> (T -> V) = 
        func(x: T) -> V = f(g(x))
      
      func double(x: int) -> int = x * 2
      func square(x: int) -> int = x * x
      func double_and_square = compose(square, double)
      
      func main() = 
        double_and_square(3)
    }
    """
    print("\nTest 3: Let-polymorphism with compose")
    ast = parse(source)
    checker = TypeChecker()
    try:
        typed_ast = checker.check_module(ast)
        print("  ✓ Type checking succeeded")
        evaluator = Evaluator()
        result = evaluator.eval_module(typed_ast)
        print("  ✓ Evaluation succeeded")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False


def test_basic_type_inference():
    """Test: Basic Hindley-Milner inference"""
    source = """
    module test
    {
      func apply[T](f: T -> T, x: T) -> T = f(x)
      
      func increment(x: int) -> int = x + 1
      
      func main() = 
        apply(increment, 5)
    }
    """
    print("\nTest 4: Basic type inference with polymorphism")
    ast = parse(source)
    checker = TypeChecker()
    try:
        typed_ast = checker.check_module(ast)
        print("  ✓ Type checking succeeded")
        evaluator = Evaluator()
        result = evaluator.eval_module(typed_ast)
        print("  ✓ Evaluation succeeded")
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        traceback.print_exc()
        return False


def test_type_error():
    """Test: Should detect type error"""
    source = """
    module test
    {
      func add(x: int, y: int) -> int = x + y
      func main() = 
        add("hello", 5)
    }
    """
    print("\nTest 5: Type error detection")
    ast = parse(source)
    checker = TypeChecker()
    try:
        typed_ast = checker.check_module(ast)
        print("  ✗ Should have failed type checking")
        return False
    except TypeCheckError:
        print("  ✓ Type error correctly detected")
        return True
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return False


def main():
    print("=" * 60)
    print("ALGOL 26 Phase 2 Type System Tests")
    print("Testing: Hindley-Milner inference, let-polymorphism")
    print("=" * 60)
    
    tests = [
        test_simple_let_polymorphism,
        test_generic_identity,
        test_let_polymorphism_in_action,
        test_basic_type_inference,
        test_type_error
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"Fatal error in {test.__name__}: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    if passed == total:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
