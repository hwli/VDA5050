package main

import (
	"log"

	"github.com/example/vda5050-backend/internal/server"
)

func main() {
	srv, err := server.New()
	if err != nil {
		log.Fatalf("failed to initialize server: %v", err)
	}

	if err := srv.Run(); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
