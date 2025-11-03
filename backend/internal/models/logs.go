package models

import "time"

// LogDescriptor represents a log file's metadata.
type LogDescriptor struct {
	Name       string    `json:"name"`
	Size       int64     `json:"size"`
	ModifiedAt time.Time `json:"modifiedAt"`
}
