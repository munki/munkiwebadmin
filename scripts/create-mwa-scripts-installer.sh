#!/bin/bash
#
# Creates a pkg installer for the preflight, postflight and
# report_broken_client scripts.
#
# Joe Wollard <joe.wollard@gmail.com> 2013.03.23
#

BUNDLE_IDENTIFIER="com.googlecode.munki.munkiwebadmin-scripts"
BUNDLE_VERSION=`date +"%Y.%m.%d"`

BASE_DIR=`dirname "${0}"`
SCRIPT_NAME=`basename "${0}"`
## clean up any existing temp directories from a previously interrupted run...
rm -rf "/tmp/${SCRIPT_NAME}"*
BUILD_DIR=`mktemp -d /tmp/${SCRIPT_NAME}.XXXXXX` || exit 1
FILE_LIST=(
	"${BASE_DIR}/munkiwebadmin-config"
	"${BASE_DIR}/preflight"
	"${BASE_DIR}/postflight"
	"${BASE_DIR}/report_broken_client"
)


if [ ! -e /usr/bin/defaults ]; then
	echo "Operating system is not OS X. Cannot continue"
	exit 1
fi

SYSTEM_VERSION=`/usr/bin/defaults read /System/Library/CoreServices/SystemVersion ProductVersion`
SYSTEM_VERSION=${SYSTEM_VERSION#*.}
SYSTEM_VERSION=${SYSTEM_VERSION%%.*}

if [ $SYSTEM_VERSION -lt 6 ]; then
	echo "OS X 10.6 or higher is required to run this script"
	exit 1
fi



MWA_HOST=""
MWA_CERT_FILE=""

# Ask the admin for the MWA_HOST and test with curl to make sure it's reachable
while [ -z "${MWA_HOST}" ]; do
	read -p "Enter the FQDN of your MWA server: " MWA_HOST
	/usr/bin/curl --max-time 5 -I -L --silent --insecure "${MWA_HOST}/lookup/ip" | grep "404 Not Found" > /dev/null
	if [ $? == 0 ]; then
		read -p "   MWA install not detected! Continue anyway? [y/N] " USE_UNREACHABLE_HOST
		if [ "${USE_UNREACHABLE_HOST}" == "y" ]; then
			break
		fi
		MWA_HOST=""
	fi
done

if [ ! `echo "${MWA_HOST}" | grep -ie "^https"` ]; then
	USE_CERT=0
else
	/usr/bin/curl --max-time 5 -I -L --silent "${MWA_HOST}/lookup/ip" > /dev/null
	if [ $? != 0 ]; then
		USE_CERT=1
	else
		USE_CERT=0
	fi
fi


# The admin is using a self-signed cert, we'll grab it from the server and
# include it in the package
if [ $USE_CERT == 1 ]; then
	echo "===OBTAINING CERT FROM ${MWA_HOST}==="
	TMP_MWA_HOST=`echo "${MWA_HOST}" | sed 's|^[^:]*://||' | sed 's|^\([^/:]*\)[/:]*.*|\1|g'`
	MWA_CERT_FILE="${BASE_DIR}/${TMP_MWA_HOST}.cert"
	echo -n | openssl s_client -connect "${TMP_MWA_HOST}":443 | sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' 1> "${MWA_CERT_FILE}"
	echo "===DONE==="
	echo "${MWA_CERT_FILE}"
	FILE_LIST+=($MWA_CERT_FILE)
fi


echo
echo "	You can specify a list of allowed network prefixes."
echo "	Doing so will prevent munki from running on any other network."
echo "	Leave this blank if you want munki to check for updates everywhere."
echo
echo "	EXAMPLE: '192.168 172.16' <-- only allows execution on 2 networks"
echo 
read -p "Specify allowed network prefixes: " MWA_ALLOWED_NETWORKS



# Create the package structure
mkdir -p "${BUILD_DIR}/usr/local/munki"
for item in ${FILE_LIST[@]}
do
	cp "${item}" "${BUILD_DIR}/usr/local/munki/"
done


# inject the data collected from the admin into the config file
BUILD_CONF="${BUILD_DIR}/usr/local/munki/munkiwebadmin-config"

# Appropriately set the value of MWA_SSL_CERTIFICATE
if [ -e "${MWA_CERT_FILE}" ]; then
	CERTFILE="/usr/local/munki/`basename \"${MWA_CERT_FILE}\"`"
else
	CERTFILE=""
fi

# write the certificate value, if any
/usr/bin/sed -i '' -e "s|^MWA_SSL_CERTIFICATE=.*$|MWA_SSL_CERTIFICATE=\"${CERTFILE}\"|" "${BUILD_CONF}"
# write the MWA host name
/usr/bin/sed -i '' -e "s|^MWA_HOST=.*$|MWA_HOST=\"$MWA_HOST\"|" "${BUILD_CONF}"
# write the allowed networks array
/usr/bin/sed -i '' -e "s|^MWA_ALLOWED_NETWORKS=.*$|MWA_ALLOWED_NETWORKS=( $MWA_ALLOWED_NETWORKS )|" "${BUILD_CONF}"

# Create a postflight script to fix permissions
SCRIPTS_DIR=`mktemp -d /tmp/${SCRIPT_NAME}.XXXXXX` || exit 1
POSTINSTALL="${SCRIPTS_DIR}/postinstall"
(
cat <<'EOF'
#!/bin/bash
source /usr/local/munki/munkiwebadmin-config
FILES=(
	"preflight"
	"postflight"
	"report_broken_client"
	"munkiwebadmin-config"
)

for item in ${FILES[@]}
do
	chmod 755 "${item}"
	chown root:wheel "${item}"
done

chmod 755 "${MWA_SSL_CERTIFICATE}"
chown root:wheel "${MWA_SSL_CERTIFICATE}"
exit 0
EOF
) > "${POSTINSTALL}"

chmod a+x "${POSTINSTALL}"


# And finally, we get to build the package
/usr/bin/pkgbuild --root "${BUILD_DIR}" \
	--scripts "${SCRIPTS_DIR}" \
	--identifier "${BUNDLE_IDENTIFIER}" \
	--version "${BUNDLE_VERSION}" \
	"munkiwebadmin_scripts-${BUNDLE_VERSION}.pkg"

echo "Cleaning up..."
if [ ! -z $MWA_CERT_FILE ];then
	if [ -e "${MWA_CERT_FILE}" ]; then
		rm "${MWA_CERT_FILE}"
	fi
fi
rm -rf "${BUILD_DIR}"
rm -rf "${SCRIPTS_DIR}"

echo
echo "Finished building munkiwebadmin_scripts-${BUNDLE_VERSION}.pkg"
echo 
