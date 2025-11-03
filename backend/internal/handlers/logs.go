package handlers

import (
	"errors"
	"net/http"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"

	logservice "github.com/example/vda5050-backend/internal/services/logs"
	"github.com/example/vda5050-backend/internal/util"
)

// LogHandler exposes endpoints for managing log files.
type LogHandler struct {
	service *logservice.Service
}

// NewLogHandler constructs a LogHandler instance.
func NewLogHandler(service *logservice.Service) *LogHandler {
	return &LogHandler{service: service}
}

// List returns available log descriptors.
func (h *LogHandler) List(c *gin.Context) {
	logs, err := h.service.List()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list logs"})
		return
	}

	c.JSON(http.StatusOK, logs)
}

// Download streams a log file to the client.
func (h *LogHandler) Download(c *gin.Context) {
	filename := c.Param("filename")
	resolved, err := h.service.Resolve(filename)
	if err != nil {
		status := http.StatusInternalServerError
		if errors.Is(err, util.ErrInvalidFilename) {
			status = http.StatusBadRequest
		}
		c.JSON(status, gin.H{"error": "invalid filename"})
		return
	}

	if _, err := os.Stat(resolved); err != nil {
		if errors.Is(err, os.ErrNotExist) {
			c.JSON(http.StatusNotFound, gin.H{"error": "log not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to access log"})
		return
	}

	c.FileAttachment(resolved, filepath.Base(resolved))
}
