// Kodex Launcher — thin wrapper that launches embedded Python
// Build: go build -ldflags "-H windowsgui -s -w" -o Kodex.exe kodex.go
//
// Flags:
//   -H windowsgui  = no console window
//   -s -w          = strip debug info (smaller exe)

package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
)

func main() {
	// Get directory where this exe lives
	exe, err := os.Executable()
	if err != nil {
		os.Exit(1)
	}
	dir := filepath.Dir(exe)

	// Path to embedded Python
	python := filepath.Join(dir, "python", "python.exe")

	// Launch Kodex via Python module
	cmd := exec.Command(python, "-m", "kodex_py.app")
	cmd.Dir = dir

	// Set environment so Python finds the app
	cmd.Env = append(os.Environ(),
		"PYTHONPATH="+filepath.Join(dir, "app"),
		"KODEX_ROOT="+dir,
	)

	// Hide the Python console window too
	cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow: true,
	}

	// Run and exit with Python's exit code
	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			os.Exit(exitErr.ExitCode())
		}
		os.Exit(1)
	}
}
