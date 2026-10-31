from __future__ import annotations

from ctypes import Structure, byref, c_float, c_int, c_void_p, cast, pointer

import pytest

from rubicon.objc import NSObject, ObjCBlock, ObjCClass, objc_method
from rubicon.objc import api as api_module
from rubicon.objc.api import AUTO, Block, ObjCBlockStruct
from rubicon.objc.runtime import objc_block, objc_id


def test_block_property_ctypes():
    BlockPropertyExample = ObjCClass("BlockPropertyExample")
    instance = BlockPropertyExample.alloc().init()
    result = ObjCBlock(instance.blockProperty, c_int, c_int, c_int)(1, 2)
    assert result == 3


def test_block_property_pytypes():
    BlockPropertyExample = ObjCClass("BlockPropertyExample")
    instance = BlockPropertyExample.alloc().init()
    result = ObjCBlock(instance.blockProperty, int, int, int)(1, 2)
    assert result == 3


def test_block_delegate_method_manual_ctypes():
    class DelegateManualC(NSObject):
        @objc_method
        def exampleMethod_(self, block):
            ObjCBlock(block, c_void_p, c_int, c_int)(2, 3)

    BlockObjectExample = ObjCClass("BlockObjectExample")
    delegate = DelegateManualC.alloc().init()
    instance = BlockObjectExample.alloc().initWithDelegate_(delegate)
    result = instance.blockExample()
    assert result == 5


def test_block_delegate_method_manual_pytypes():
    class DelegateManualPY(NSObject):
        @objc_method
        def exampleMethod_(self, block):
            ObjCBlock(block, None, int, int)(2, 3)

    BlockObjectExample = ObjCClass("BlockObjectExample")
    delegate = DelegateManualPY.alloc().init()
    instance = BlockObjectExample.alloc().initWithDelegate_(delegate)
    result = instance.blockExample()
    assert result == 5


def test_block_delegate_auto():
    class DelegateAuto(NSObject):
        @objc_method
        def exampleMethod_(self, block: objc_block):
            block(4, 5)

    BlockObjectExample = ObjCClass("BlockObjectExample")
    delegate = DelegateAuto.alloc().init()
    instance = BlockObjectExample.alloc().initWithDelegate_(delegate)
    result = instance.blockExample()
    assert result == 9


def test_block_delegate_manual_struct():
    class BlockStruct(Structure):
        _fields_ = [
            ("a", c_int),
            ("b", c_int),
        ]

    class DelegateManualStruct(NSObject):
        @objc_method
        def structBlockMethod_(self, block: objc_block) -> int:
            return ObjCBlock(block, int, BlockStruct)(BlockStruct(42, 43))

    BlockObjectExample = ObjCClass("BlockObjectExample")
    delegate = DelegateManualStruct.alloc().init()
    instance = BlockObjectExample.alloc().initWithDelegate_(delegate)
    result = instance.structBlockExample()
    assert result == 85


def test_block_delegate_auto_struct():
    class BlockStruct(Structure):
        _fields_ = [
            ("a", c_int),
            ("b", c_int),
        ]

    class DelegateAutoStruct(NSObject):
        @objc_method
        def structBlockMethod_(self, block: objc_block) -> int:
            return block(BlockStruct(42, 43))

    BlockObjectExample = ObjCClass("BlockObjectExample")
    delegate = DelegateAutoStruct.alloc().init()
    instance = BlockObjectExample.alloc().initWithDelegate_(delegate)
    result = instance.structBlockExample()
    assert result == 85


def test_block_delegate_auto_struct_mismatch():
    class BadBlockStruct(Structure):
        _fields_ = [
            ("a", c_float),
            ("b", c_int),
        ]

    class BadDelegateAutoStruct(NSObject):
        @objc_method
        def structBlockMethod_(self, block: objc_block) -> int:
            try:
                # block accepts an anonymous structure with 2 int arguments
                # Passing in BadBlockStruct should raise a type error because
                # the structure's shape doesn't match.
                return block(BadBlockStruct(2.71828, 43))
            except TypeError:
                # Ideally, this would be raised as an ObjC error;
                # however, at least for now, that doesn't happen.
                return -99

    BlockObjectExample = ObjCClass("BlockObjectExample")
    delegate = BadDelegateAutoStruct.alloc().init()
    instance = BlockObjectExample.alloc().initWithDelegate_(delegate)
    result = instance.structBlockExample()
    assert result == -99


def test_block_receiver():
    BlockReceiverExample = ObjCClass("BlockReceiverExample")
    instance = BlockReceiverExample.alloc().init()

    values = []

    def block(a: int, b: int) -> int:
        values.append(a + b)
        return 42

    result = instance.receiverMethod_(block)

    assert values == [27]
    assert result == 42


def test_block_receiver_no_return_annotation():
    BlockReceiverExample = ObjCClass("BlockReceiverExample")
    instance = BlockReceiverExample.alloc().init()

    def block(a: int, b: int):
        return a + b

    with pytest.raises(ValueError):
        instance.receiverMethod_(block)


def test_block_receiver_missing_arg_annotation():
    BlockReceiverExample = ObjCClass("BlockReceiverExample")
    instance = BlockReceiverExample.alloc().init()

    def block(a: int, b) -> int:
        return a + b

    with pytest.raises(ValueError):
        instance.receiverMethod_(block)


def test_block_receiver_lambda():
    BlockReceiverExample = ObjCClass("BlockReceiverExample")
    instance = BlockReceiverExample.alloc().init()
    with pytest.raises(ValueError):
        instance.receiverMethod_(lambda a, b: a + b)


def test_block_receiver_explicit():
    BlockReceiverExample = ObjCClass("BlockReceiverExample")
    instance = BlockReceiverExample.alloc().init()

    values = []

    block = Block(lambda a, b: values.append(a + b), None, int, int)
    instance.receiverMethod_(block)

    assert values == [27]


def test_block_round_trip():
    BlockRoundTrip = ObjCClass("BlockRoundTrip")
    instance = BlockRoundTrip.alloc().init()

    def block(a: int, b: int) -> int:
        return a + b

    returned_block = instance.roundTrip_(block)
    assert returned_block(8, 9) == 17


def test_block_round_trip_no_arguments():
    """A block that takes no arguments can be created with both ways of specifying
    types."""
    BlockRoundTrip = ObjCClass("BlockRoundTrip")
    instance = BlockRoundTrip.alloc().init()

    @Block
    def block_1() -> c_int:
        return 42

    returned_block_1 = instance.roundTripNoArgs(block_1)
    assert returned_block_1() == 42

    block_2 = Block(lambda: 42, c_int)
    returned_block_2 = instance.roundTripNoArgs(block_2)
    assert returned_block_2() == 42


def test_block_bound_method():
    """A bound method with type annotations can be wrapped in a block."""

    class Handler:
        def no_args(self) -> c_int:
            return 42

        def two_args(self, x: c_int, y: c_int) -> c_int:
            return x + y

    handler = Handler()
    no_args_block = Block(handler.no_args)
    two_args_block = Block(handler.two_args)

    BlockRoundTrip = ObjCClass("BlockRoundTrip")
    instance = BlockRoundTrip.alloc().init()

    returned_no_args_block = instance.roundTripNoArgs(no_args_block)
    assert returned_no_args_block() == 42

    returned_two_args_block = instance.roundTrip(two_args_block)
    assert returned_two_args_block(12, 34) == 46


def test_nil_block():
    """A None block argument is passed through as nil."""

    class TakesBlock(NSObject):
        @objc_method
        def takeBlock_(self, block: objc_block) -> c_int:
            return 0 if block is None else 1

    assert TakesBlock.alloc().init().takeBlock_(None) == 0


def test_objc_block():
    """ObjCBlock reports its signature and rejects AUTO without one."""
    block = ObjCClass("BlockPropertyExample").alloc().init().blockProperty
    text = repr(ObjCBlock(block, c_int, c_int, c_int))
    assert text.startswith("<ObjCBlock@")
    assert "has_signature" in text

    with pytest.raises(ValueError, match="argtypes with restype AUTO"):
        ObjCBlock(block, AUTO, c_int)

    descriptor_type = api_module.create_block_descriptor_struct(False, False)
    descriptor = descriptor_type()
    literal = ObjCBlockStruct()
    literal.flags = 0
    literal.descriptor = cast(byref(descriptor), c_void_p)
    raw = cast(pointer(literal), objc_id)
    with pytest.raises(ValueError, match="without signatures"):
        ObjCBlock(raw)
    assert "has_helpers" not in repr(ObjCBlock(raw, c_int))

    helper = Block(lambda value: value, c_int, c_int)
    assert "has_helpers" in repr(ObjCBlock(helper.block, c_int, c_int))


def test_block():
    """Block rejects bad callables and tracks copies."""
    with pytest.raises(TypeError, match="must be callable"):
        Block(object())
    with pytest.raises(ValueError, match="without a restype"):
        Block(lambda value: value, api_module.NOTHING, c_int)

    class Uninspectable:
        def __call__(self):
            return None

        @property
        def __signature__(self):
            raise ValueError("unavailable")

    with pytest.raises(ValueError, match="signature information"):
        Block(Uninspectable())

    block = Block(lambda value: value, c_int, c_int)
    block.copy_helper(1, 2)
    assert Block._keep_alive_blocks_[1] is block
    block.dispose_helper(1)
    assert 1 not in Block._keep_alive_blocks_
