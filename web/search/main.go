package main

import (
	"log"
)

func main() {
	if err := initDatabase("postgres://localhost/postgres"); err != nil {
		log.Fatalf("failed starting db: %v", err)
	}
	defer closeDatabase()

	log.Fatal(listen(":8080"))
}
