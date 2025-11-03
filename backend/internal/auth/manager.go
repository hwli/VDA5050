package auth

import (
	"crypto/rand"
	"encoding/base64"
	"errors"
	"sync"
)

var ErrInvalidCredentials = errors.New("invalid credentials")

// Manager encapsulates authentication and token management logic.
type Manager struct {
	users  map[string]string
	tokens *tokenStore
}

// NewManager constructs a Manager with the provided credential store.
func NewManager(users map[string]string) *Manager {
	return &Manager{
		users:  users,
		tokens: newTokenStore(),
	}
}

// Authenticate validates the provided credentials and returns a bearer token on success.
func (m *Manager) Authenticate(username, password string) (string, error) {
	expected, ok := m.users[username]
	if !ok || expected != password {
		return "", ErrInvalidCredentials
	}

	token, err := generateToken()
	if err != nil {
		return "", err
	}

	m.tokens.set(token, username)
	return token, nil
}

// Validate returns the username associated with the token, if present.
func (m *Manager) Validate(token string) (string, bool) {
	return m.tokens.get(token)
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
	s.tokens[token] = username
	s.mu.Unlock()
}

func (s *tokenStore) get(token string) (string, bool) {
	s.mu.RLock()
	username, ok := s.tokens[token]
	s.mu.RUnlock()
	return username, ok
}

func generateToken() (string, error) {
	buf := make([]byte, 32)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(buf), nil
}
