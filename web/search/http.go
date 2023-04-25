package main

import (
	"embed"
	"html/template"
	"net/http"
	"path/filepath"

	"github.com/mca3/mwr"
)

type htmlData struct {
	Title string

	Q       string
	Results []result
}

//go:embed views
var views embed.FS

var tmpl = template.Must(template.ParseFS(views, "views/*.html"))

func serveFile(c *mwr.Ctx) error {
	pth := filepath.Join("./static", c.Path())

	return c.SendFile(pth)
}

func search(c *mwr.Ctx) error {
	query := c.Query("q")
	res, err := searchDatabase(c.Context(), query, 0)
	if err != nil {
		return err
	}

	data := htmlData{
		Title:   "Search",
		Q:       query,
		Results: res,
	}

	return tmpl.ExecuteTemplate(c, "index.html", data)
}

func listen(addr string) error {
	h := &mwr.Handler{}
	srv := &http.Server{Addr: addr, Handler: h}

	h.Get("/", search)
	h.Get("", serveFile)

	return srv.ListenAndServe()
}
