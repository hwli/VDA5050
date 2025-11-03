package upgrade

import (
	"fmt"
	"io"
	"os"

	"github.com/example/vda5050-backend/internal/util"
)

// Service handles persistence of uploaded upgrade artifacts.
type Service struct {
	dir string
}

// New constructs a Service bound to the provided directory.
func New(dir string) *Service {
	return &Service{dir: dir}
}

// Save writes the contents of the provided reader to disk using the supplied filename.
func (s *Service) Save(filename string, source io.Reader) (string, error) {
	resolved, err := util.ResolveWithin(s.dir, filename)
	if err != nil {
		return "", err
	}

	out, err := os.Create(resolved)
	if err != nil {
		return "", fmt.Errorf("create upgrade artifact: %w", err)
	}
	defer out.Close()

	if _, err := io.Copy(out, source); err != nil {
		return "", fmt.Errorf("write upgrade artifact: %w", err)
	}

	return resolved, nil
}
