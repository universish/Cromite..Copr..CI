# Fedora COPR SCM (make_srpm) entegrasyonu için Makefile
# Depo: https://github.com/universish/Cromite..Copr..CI
# COPR: https://copr.fedorainfracloud.org/coprs/universish/Cromite../

SPEC ?= cromite.spec
outdir ?= .

.PHONY: srpm
srpm:
	if command -v dnf >/dev/null 2>&1; then \
		dnf -y install rpmdevtools rpm-build curl jq tar gzip desktop-file-utils libappstream-glib; \
	elif command -v zypper >/dev/null 2>&1; then \
		zypper --non-interactive install rpm-build curl jq tar gzip desktop-file-utils appstream-glib; \
	fi
	mkdir -p /tmp/rpmbuild/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
	cp -f *.desktop *.sh *.xml /tmp/rpmbuild/SOURCES/ 2>/dev/null || :
	SOURCE_URL=$$(rpmspec -P "$(SPEC)" | awk '/^Source0:/ {print $$2}'); \
	curl -fL --retry 3 -o "/tmp/rpmbuild/SOURCES/chrome-lin64.tar.gz" "$$SOURCE_URL"
	rpmbuild -bs \
		--define "_topdir /tmp/rpmbuild" \
		--define "_sourcedir /tmp/rpmbuild/SOURCES" \
		--define "_srcrpmdir $(outdir)" \
		"$(SPEC)"
