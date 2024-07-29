DOCNAME=icecap

all: icecap

.PHONY: clean

icecap:
	pdflatex $(DOCNAME).tex
	bibtex $(DOCNAME).aux
	pdflatex $(DOCNAME).tex
	pdflatex $(DOCNAME).tex


clean:
	rm -f *.pdf *.blg *.bbl *.aux *.log *.out *.toc
