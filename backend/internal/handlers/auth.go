package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"github.com/example/vda5050-backend/internal/auth"
	"github.com/example/vda5050-backend/internal/models"
)

// AuthHandler exposes authentication related endpoints.
type AuthHandler struct {
	manager *auth.Manager
}

// NewAuthHandler constructs an AuthHandler.
func NewAuthHandler(manager *auth.Manager) *AuthHandler {
	return &AuthHandler{manager: manager}
}

// Login validates user credentials and returns a bearer token.
func (h *AuthHandler) Login(c *gin.Context) {
	var req models.LoginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}

	token, err := h.manager.Authenticate(req.Username, req.Password)
	if err != nil {
		if err == auth.ErrInvalidCredentials {
			c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid credentials"})
			return
		}
		c.JSON(http.StatusInternalServerError, gin.H{"error": "unable to generate token"})
		return
	}

	c.JSON(http.StatusOK, models.LoginResponse{Token: token})
}

// Me returns the authenticated user's profile information.
func (h *AuthHandler) Me(c *gin.Context) {
	username := c.GetString("username")
	c.JSON(http.StatusOK, gin.H{"username": username})
}
