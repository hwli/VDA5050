package handlers

import (
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"

	upgradeservice "github.com/example/vda5050-backend/internal/services/upgrade"
	"github.com/example/vda5050-backend/internal/util"
)

// UpgradeHandler exposes endpoints to upload upgrade artifacts.
type UpgradeHandler struct {
	service *upgradeservice.Service
}

// NewUpgradeHandler constructs an UpgradeHandler instance.
func NewUpgradeHandler(service *upgradeservice.Service) *UpgradeHandler {
	return &UpgradeHandler{service: service}
}

// Upload persists an uploaded upgrade file to disk.
func (h *UpgradeHandler) Upload(c *gin.Context) {
	file, header, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "file upload required"})
		return
	}
	defer file.Close()

	if header == nil || header.Filename == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "file upload required"})
		return
	}

	_, err = h.service.Save(header.Filename, file)
	if err != nil {
		status := http.StatusInternalServerError
		if errors.Is(err, util.ErrInvalidFilename) {
			status = http.StatusBadRequest
		}
		c.JSON(status, gin.H{"error": "failed to save upgrade"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":  "upgrade uploaded successfully",
		"filename": header.Filename,
	})
}
