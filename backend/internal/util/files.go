package util

import (
	"errors"
	"os"
	"path/filepath"
	"strings"
)

var ErrInvalidFilename = errors.New("invalid filename")

// ResolveWithin sanitizes the provided file name and ensures it remains within the base directory.
func ResolveWithin(baseDir, name string) (string, error) {
	cleaned := filepath.Clean(name)
	if cleaned == "." || cleaned == "" {
		return "", ErrInvalidFilename
	}
	if strings.Contains(cleaned, "..") || strings.HasPrefix(cleaned, string(os.PathSeparator)) {
		return "", ErrInvalidFilename
	}

	return filepath.Join(baseDir, filepath.Base(cleaned)), nil
}
