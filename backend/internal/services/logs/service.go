package logs

import (
	"os"
	"sort"

	"github.com/example/vda5050-backend/internal/models"
	"github.com/example/vda5050-backend/internal/util"
)

// Service provides access to log file metadata and contents.
type Service struct {
	dir string
}

// New constructs a Service bound to the given directory.
func New(dir string) *Service {
	return &Service{dir: dir}
}

// List returns descriptors for available log files.
func (s *Service) List() ([]models.LogDescriptor, error) {
	entries, err := os.ReadDir(s.dir)
	if err != nil {
		return nil, err
	}

	descriptors := make([]models.LogDescriptor, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		info, err := entry.Info()
		if err != nil {
			continue
		}
		descriptors = append(descriptors, models.LogDescriptor{
			Name:       entry.Name(),
			Size:       info.Size(),
			ModifiedAt: info.ModTime(),
		})
	}

	sort.SliceStable(descriptors, func(i, j int) bool {
		return descriptors[i].ModifiedAt.After(descriptors[j].ModifiedAt)
	})

	return descriptors, nil
}

// Resolve returns the absolute path of the requested log file.
func (s *Service) Resolve(name string) (string, error) {
	return util.ResolveWithin(s.dir, name)
}
