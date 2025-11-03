package config

import (
	"fmt"
	"os"
	"strings"
)

const (
	LogDir    = "data/logs"
	UploadDir = "data/uploads"
)

var defaultUsers = map[string]string{
	"admin": "password123",
}

// EnsureDirectories guarantees that required filesystem directories exist.
func EnsureDirectories() error {
	for _, dir := range []string{LogDir, UploadDir} {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return fmt.Errorf("create directory %s: %w", dir, err)
		}
	}
	return nil
}

// Port resolves the port that the HTTP server should bind to.
func Port() string {
	if value := os.Getenv("PORT"); value != "" {
		return value
	}
	return "8080"
}

// AllowedOrigins returns the CORS allow list based on configuration.
func AllowedOrigins() []string {
	if value := os.Getenv("ALLOWED_ORIGINS"); value != "" {
		parts := strings.Split(value, ",")
		origins := make([]string, 0, len(parts))
		for _, part := range parts {
			trimmed := strings.TrimSpace(part)
			if trimmed != "" {
				origins = append(origins, trimmed)
			}
		}
		if len(origins) > 0 {
			return origins
		}
	}
	return []string{"http://localhost:5173"}
}

// Users returns the configured authentication credentials.
func Users() map[string]string {
	users := make(map[string]string, len(defaultUsers))
	for username, password := range defaultUsers {
		users[username] = password
	}
	return users
}
