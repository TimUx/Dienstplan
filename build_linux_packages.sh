#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${1:-}"

if [ -z "${VERSION}" ]; then
  VERSION="$(python3 - <<'PY'
from datetime import datetime
print(datetime.now().strftime("2.2.%Y%m%d%H%M"))
PY
)"
fi

DIST_APP_DIR="${ROOT_DIR}/dist/Dienstplan"
if [ ! -d "${DIST_APP_DIR}" ]; then
  echo "PyInstaller output not found at dist/Dienstplan"
  echo "Run: python3 -m PyInstaller Dienstplan.spec"
  exit 1
fi

OUT_DIR="${ROOT_DIR}/dist/packages"
STAGE_DIR="${ROOT_DIR}/dist/package-stage"
DEB_DIR="${STAGE_DIR}/deb"
RPM_TOP="${STAGE_DIR}/rpmbuild"

rm -rf "${STAGE_DIR}"
mkdir -p "${OUT_DIR}" "${DEB_DIR}"

echo "[1/4] Preparing shared root filesystem..."
mkdir -p "${DEB_DIR}/opt/dienstplan"
mkdir -p "${DEB_DIR}/usr/bin" "${DEB_DIR}/usr/sbin" "${DEB_DIR}/usr/lib/systemd/system"
cp -a "${DIST_APP_DIR}" "${DEB_DIR}/opt/dienstplan/Dienstplan"

install -m 0755 "${ROOT_DIR}/packaging/linux/common/dienstplan" "${DEB_DIR}/usr/bin/dienstplan"
install -m 0755 "${ROOT_DIR}/packaging/linux/common/dienstplan-setup-admin.sh" "${DEB_DIR}/usr/sbin/dienstplan-setup-admin"
install -m 0644 "${ROOT_DIR}/packaging/linux/common/dienstplan.service" "${DEB_DIR}/usr/lib/systemd/system/dienstplan.service"
mkdir -p "${DEB_DIR}/var/lib/dienstplan/data"

echo "[2/4] Building .deb package..."
if ! command -v dpkg-deb >/dev/null 2>&1; then
  echo "dpkg-deb not found. Install dpkg-dev to build .deb."
  exit 1
fi

mkdir -p "${DEB_DIR}/DEBIAN"
sed "s/__VERSION__/${VERSION}/g" "${ROOT_DIR}/packaging/linux/deb/control" > "${DEB_DIR}/DEBIAN/control"
install -m 0755 "${ROOT_DIR}/packaging/linux/deb/postinst" "${DEB_DIR}/DEBIAN/postinst"
install -m 0755 "${ROOT_DIR}/packaging/linux/deb/prerm" "${DEB_DIR}/DEBIAN/prerm"

DEB_OUT="${OUT_DIR}/dienstplan_${VERSION}_amd64.deb"
dpkg-deb --build "${DEB_DIR}" "${DEB_OUT}"

echo "[3/4] Building .rpm package..."
if ! command -v rpmbuild >/dev/null 2>&1; then
  echo "rpmbuild not found. Install rpm-build to build .rpm."
  exit 1
fi

mkdir -p "${RPM_TOP}/"{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

mkdir -p "${STAGE_DIR}/rootfs"
cp -a "${DEB_DIR}/opt" "${STAGE_DIR}/rootfs/opt"
cp -a "${DEB_DIR}/usr" "${STAGE_DIR}/rootfs/usr"
cp -a "${DEB_DIR}/var" "${STAGE_DIR}/rootfs/var"
tar -czf "${RPM_TOP}/SOURCES/dienstplan-root.tar.gz" -C "${STAGE_DIR}" rootfs

SPEC_PATH="${RPM_TOP}/SPECS/dienstplan.spec"
sed "s/__VERSION__/${VERSION}/g" "${ROOT_DIR}/packaging/linux/rpm/dienstplan.spec.template" > "${SPEC_PATH}"
rpmbuild --define "_topdir ${RPM_TOP}" -bb "${SPEC_PATH}"

cp -a "${RPM_TOP}/RPMS/"*/*.rpm "${OUT_DIR}/"

echo "[4/4] Done."
echo "Created packages:"
ls -1 "${OUT_DIR}"
