# Metadata comparison

## traversal

Archive member count: original `1`, filtered `1`.
Core member fields equal: `True`

## absolute

Archive member count: original `1`, filtered `1`.
Core member fields equal: `True`

## symlink

Archive member count: original `2`, filtered `2`.
Core member fields equal: `True`

## hardlink

Archive member count: original `2`, filtered `2`.
Core member fields equal: `True`

## sparse

Archive member count: original `1`, filtered `1`.
Original sparse map: `[(0, 4096), (1048576, 4096), (8388608, 3), (8388611, 0)]`
Filtered sparse map: `None`
Filtered Python manifest error: `ValueError: not enough values to unpack (expected 2, got 1)`
Filtered GNU tar list status: `2`

## numeric-owner

Archive member count: original `1`, filtered `1`.
Core member fields equal: `True`

## mode-bits

Archive member count: original `1`, filtered `1`.
Core member fields equal: `True`

## timestamps

Archive member count: original `1`, filtered `1`.
Core member fields equal: `True`

## xattr

Archive member count: original `1`, filtered `1`.
Original pax headers: `{'SCHILY.xattr.user.lf14': 'corpus'}`
Filtered pax headers: `{'SCHILY.xattr.user.lf14': 'corpus'}`
