package main

import (
	"crypto/rand"
	"encoding/base64"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

const (
	logDir    = "data/logs"
	uploadDir = "data/uploads"
)

var users = map[string]string{
	"admin": "password123",
}

type tokenStore struct {
	mu     sync.RWMutex
	tokens map[string]string
}

func newTokenStore() *tokenStore {
	return &tokenStore{tokens: make(map[string]string)}
}

func (s *tokenStore) set(token, username string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.tokens[token] = username
}

func (s *tokenStore) get(token string) (string, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	username, ok := s.tokens[token]
	return username, ok
}

var tokens = newTokenStore()

type loginRequest struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

type loginResponse struct {
	Token string `json:"token"`
}

type logDescriptor struct {
	Name       string    `json:"name"`
	Size       int64     `json:"size"`
	ModifiedAt time.Time `json:"modifiedAt"`
}

func main() {
	ensureDirectories()

	router := gin.Default()
	router.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:5173"},
		AllowMethods:     []string{"GET", "POST", "OPTIONS"},
		AllowHeaders:     []string{"Authorization", "Content-Type"},
		ExposeHeaders:    []string{"Content-Disposition"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	api := router.Group("/api")
	api.POST("/login", handleLogin)

	auth := api.Group("/")
	auth.Use(authMiddleware())
	auth.GET("/logs", handleListLogs)
	auth.GET("/logs/:filename", handleDownloadLog)
	auth.POST("/upgrade", handleUpgrade)
	auth.GET("/me", handleMe)

	port := getEnv("PORT", "8080")
	if err := router.Run(":" + port); err != nil {
		panic(err)
	}
}

func ensureDirectories() {
	for _, dir := range []string{logDir, uploadDir} {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			panic(fmt.Sprintf("failed to create directory %s: %v", dir, err))
		}
	}
}

func handleLogin(c *gin.Context) {
	var req loginRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}

	expectedPassword, ok := users[req.Username]
	if !ok || expectedPassword != req.Password {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "invalid credentials"})
		return
	}

	token, err := generateToken()
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "unable to generate token"})
		return
	}

	tokens.set(token, req.Username)
	c.JSON(http.StatusOK, loginResponse{Token: token})
}

func handleMe(c *gin.Context) {
	username := c.GetString("username")
	c.JSON(http.StatusOK, gin.H{"username": username})
}

func handleListLogs(c *gin.Context) {
	entries, err := os.ReadDir(logDir)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to list logs"})
		return
	}

	descriptors := make([]logDescriptor, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() {
			continue
		}
		info, err := entry.Info()
		if err != nil {
			continue
		}
		descriptors = append(descriptors, logDescriptor{
			Name:       entry.Name(),
			Size:       info.Size(),
			ModifiedAt: info.ModTime(),
		})
	}

	c.JSON(http.StatusOK, descriptors)
}

func handleDownloadLog(c *gin.Context) {
	filename := c.Param("filename")
	resolved, err := resolvePath(logDir, filename)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid filename"})
		return
	}

	if _, err := os.Stat(resolved); errors.Is(err, os.ErrNotExist) {
		c.JSON(http.StatusNotFound, gin.H{"error": "log not found"})
		return
	} else if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to access log"})
		return
	}

	c.FileAttachment(resolved, filepath.Base(resolved))
}

func handleUpgrade(c *gin.Context) {
	file, header, err := c.Request.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "file upload required"})
		return
	}
	defer file.Close()

	resolved, err := resolvePath(uploadDir, header.Filename)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid filename"})
		return
	}

	out, err := os.Create(resolved)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to store upgrade"})
		return
	}
	defer out.Close()

	if _, err := io.Copy(out, file); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to save upgrade"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"message":  "upgrade uploaded successfully",
		"filename": header.Filename,
	})
}

func authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		header := c.GetHeader("Authorization")
		if header == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "missing authorization header"})
			return
		}

		parts := strings.SplitN(header, " ", 2)
		if len(parts) != 2 || !strings.EqualFold(parts[0], "Bearer") {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid authorization header"})
			return
		}

		token := parts[1]
		username, ok := tokens.get(token)
		if !ok {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "invalid or expired token"})
			return
		}

		c.Set("username", username)
		c.Next()
	}
}

func resolvePath(baseDir, name string) (string, error) {
	cleaned := filepath.Clean(name)
	if cleaned == "." || cleaned == "" {
		return "", errors.New("invalid filename")
	}
	if strings.Contains(cleaned, "..") || strings.HasPrefix(cleaned, string(os.PathSeparator)) {
		return "", errors.New("invalid filename")
	}

	fullPath := filepath.Join(baseDir, filepath.Base(cleaned))
	return fullPath, nil
}

func generateToken() (string, error) {
	buf := make([]byte, 32)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(buf), nil
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
