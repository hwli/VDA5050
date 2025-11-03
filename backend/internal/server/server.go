package server

import (
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"

	"github.com/example/vda5050-backend/internal/auth"
	"github.com/example/vda5050-backend/internal/config"
	"github.com/example/vda5050-backend/internal/handlers"
	"github.com/example/vda5050-backend/internal/middleware"
	logservice "github.com/example/vda5050-backend/internal/services/logs"
	upgradeservice "github.com/example/vda5050-backend/internal/services/upgrade"
)

// Server wraps the Gin engine and exposes startup logic.
type Server struct {
	engine *gin.Engine
	port   string
}

// New wires dependencies and constructs a Server instance.
func New() (*Server, error) {
	if err := config.EnsureDirectories(); err != nil {
		return nil, err
	}

	authManager := auth.NewManager(config.Users())
	logService := logservice.New(config.LogDir)
	upgradeService := upgradeservice.New(config.UploadDir)

	authHandler := handlers.NewAuthHandler(authManager)
	logHandler := handlers.NewLogHandler(logService)
	upgradeHandler := handlers.NewUpgradeHandler(upgradeService)

	router := gin.Default()
	router.Use(cors.New(cors.Config{
		AllowOrigins:     config.AllowedOrigins(),
		AllowMethods:     []string{"GET", "POST", "OPTIONS"},
		AllowHeaders:     []string{"Authorization", "Content-Type"},
		ExposeHeaders:    []string{"Content-Disposition"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	api := router.Group("/api")
	api.POST("/login", authHandler.Login)

	authenticated := api.Group("/")
	authenticated.Use(middleware.Authenticated(authManager))
	authenticated.GET("/logs", logHandler.List)
	authenticated.GET("/logs/:filename", logHandler.Download)
	authenticated.POST("/upgrade", upgradeHandler.Upload)
	authenticated.GET("/me", authHandler.Me)

	return &Server{
		engine: router,
		port:   config.Port(),
	}, nil
}

// Run starts the underlying Gin engine.
func (s *Server) Run() error {
	return s.engine.Run(":" + s.port)
}
