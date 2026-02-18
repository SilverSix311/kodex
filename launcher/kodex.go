// Kodex Launcher — thin wrapper that launches embedded Python
//
// Build both versions:
//   go build -ldflags "-H windowsgui -s -w" -o Kodex.exe kodex.go
//   go build -ldflags "-s -w" -o Kodex-Debug.exe kodex.go
//
// Kodex.exe      = no console, silent operation
// Kodex-Debug.exe = console visible, verbose logging

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"time"
)

var debug bool

func log(format string, args ...interface{}) {
	if debug {
		timestamp := time.Now().Format("15:04:05.000")
		fmt.Printf("[%s] %s\n", timestamp, fmt.Sprintf(format, args...))
	}
}

func main() {
	// Detect debug mode from executable name
	exe, err := os.Executable()
	if err != nil {
		fmt.Println("ERROR: Cannot determine executable path:", err)
		os.Exit(1)
	}

	debug = strings.Contains(strings.ToLower(filepath.Base(exe)), "debug")

	if debug {
		fmt.Println("╔════════════════════════════════════════╗")
		fmt.Println("║         Kodex Debug Launcher           ║")
		fmt.Println("╚════════════════════════════════════════╝")
		fmt.Println()
	}

	dir := filepath.Dir(exe)
	log("Launcher directory: %s", dir)

	// Verify embedded Python exists
	pythonExe := filepath.Join(dir, "python", "python.exe")
	log("Looking for Python at: %s", pythonExe)

	if _, err := os.Stat(pythonExe); os.IsNotExist(err) {
		msg := fmt.Sprintf("ERROR: Embedded Python not found at:\n%s\n\nMake sure the 'python' folder exists next to this exe.", pythonExe)
		if debug {
			fmt.Println(msg)
			fmt.Println("\nPress Enter to exit...")
			fmt.Scanln()
		}
		os.Exit(1)
	}
	log("✓ Python found")

	// Verify app directory exists
	appDir := filepath.Join(dir, "app")
	log("Looking for app at: %s", appDir)

	if _, err := os.Stat(appDir); os.IsNotExist(err) {
		msg := fmt.Sprintf("ERROR: App directory not found at:\n%s\n\nMake sure the 'app' folder exists next to this exe.", appDir)
		if debug {
			fmt.Println(msg)
			fmt.Println("\nPress Enter to exit...")
			fmt.Scanln()
		}
		os.Exit(1)
	}
	log("✓ App directory found")

	// Check for kodex_py module
	kodexModule := filepath.Join(appDir, "kodex_py")
	log("Looking for kodex_py module at: %s", kodexModule)

	if _, err := os.Stat(kodexModule); os.IsNotExist(err) {
		msg := fmt.Sprintf("ERROR: kodex_py module not found at:\n%s", kodexModule)
		if debug {
			fmt.Println(msg)
			fmt.Println("\nPress Enter to exit...")
			fmt.Scanln()
		}
		os.Exit(1)
	}
	log("✓ kodex_py module found")

	// Build command
	// -m kodex_py runs __main__.py which calls cli()
	// We pass "run" to start the engine + tray
	cmd := exec.Command(pythonExe, "-m", "kodex_py", "run")
	cmd.Dir = dir

	// Set environment
	env := os.Environ()
	env = append(env, "PYTHONPATH="+appDir)
	env = append(env, "KODEX_ROOT="+dir)
	if debug {
		env = append(env, "KODEX_DEBUG=1")
	}
	cmd.Env = env

	log("PYTHONPATH=%s", appDir)
	log("KODEX_ROOT=%s", dir)
	log("Command: %s -m kodex_py run", pythonExe)

	if debug {
		// In debug mode, show Python's output
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		fmt.Println("\n--- Python Output ---")
	} else {
		// In normal mode, hide Python's console window
		cmd.SysProcAttr = &syscall.SysProcAttr{
			HideWindow: true,
		}
	}

	// Run
	log("Starting Kodex...")
	err = cmd.Run()

	if err != nil {
		if debug {
			fmt.Printf("\n--- Kodex exited with error ---\n%v\n", err)
			if exitErr, ok := err.(*exec.ExitError); ok {
				fmt.Printf("Exit code: %d\n", exitErr.ExitCode())
			}
			fmt.Println("\nPress Enter to exit...")
			fmt.Scanln()
		}
		if exitErr, ok := err.(*exec.ExitError); ok {
			os.Exit(exitErr.ExitCode())
		}
		os.Exit(1)
	}

	if debug {
		fmt.Println("\n--- Kodex exited normally ---")
		fmt.Println("Press Enter to exit...")
		fmt.Scanln()
	}
}
