package main

import (
	"fmt"
	"math/bits"
	"runtime"
	"unsafe"

	"golang.org/x/sys/unix"
)

func reset() {
	_, _, _ = unix.Syscall(unix.SYS_SET_MEMPOLICY, uintptr(unix.MPOL_DEFAULT), 0, 0)
}

func main() {
	if bits.UintSize != 64 {
		panic("64-bit host required")
	}
	runtime.LockOSThread()
	defer runtime.UnlockOSThread()

	dynamic := unix.NewCPUSet(64)
	dynamic.Set(63)
	dynamicErr := unix.SetMemPolicyDynamic(unix.MPOL_BIND|unix.MPOL_F_RELATIVE_NODES, dynamic)
	if dynamicErr == nil {
		reset()
	}

	var fixed unix.CPUSet
	fixed.Set(1023)
	fixedErr := unix.SetMemPolicy(unix.MPOL_BIND|unix.MPOL_F_RELATIVE_NODES, &fixed)
	if fixedErr == nil {
		reset()
	}

	rawMask := []uintptr{uintptr(1) << 63}
	_, _, raw64 := unix.Syscall(
		unix.SYS_SET_MEMPOLICY,
		uintptr(unix.MPOL_BIND|unix.MPOL_F_RELATIVE_NODES),
		uintptr(unsafe.Pointer(&rawMask[0])),
		64,
	)
	if raw64 == 0 {
		reset()
	}
	_, _, raw65 := unix.Syscall(
		unix.SYS_SET_MEMPOLICY,
		uintptr(unix.MPOL_BIND|unix.MPOL_F_RELATIVE_NODES),
		uintptr(unsafe.Pointer(&rawMask[0])),
		65,
	)
	if raw65 == 0 {
		reset()
	}

	fmt.Printf("dynamic=%v fixed=%v raw64=%v raw65=%v\n", dynamicErr, fixedErr, raw64, raw65)
}
