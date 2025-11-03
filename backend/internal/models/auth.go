package models

// LoginRequest represents the payload for authentication requests.
type LoginRequest struct {
	Username string `json:"username" binding:"required"`
	Password string `json:"password" binding:"required"`
}

// LoginResponse describes the structure of a login response.
type LoginResponse struct {
	Token string `json:"token"`
}
