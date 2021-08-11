# Use this script like this:
#
# . ${WOH_PATH}/add_path.sh
#
# unix: source ${WOH_PATH}/add_path.sh
#
if [ -z ${WOH_PATH} ]; then
	echo "WOH_PATH must be set before including this script."
else
#	WOH_ADD_PATHS_EXTRAS="${WOH_PATH}/components/esptool_py/esptool"
#	WOH_ADD_PATHS_EXTRAS="${WOH_ADD_PATHS_EXTRAS}:${WOH_PATH}/components/espcoredump"
#	WOH_ADD_PATHS_EXTRAS="${WOH_ADD_PATHS_EXTRAS}:${WOH_PATH}/components/partition_table/"
	WOH_ADD_PATHS_EXTRAS="${WOH_ADD_PATHS_EXTRAS}:${WOH_PATH}/tools/"
	export PATH="${WOH_ADD_PATHS_EXTRAS}:${PATH}"
	echo "Added to PATH: ${WOH_ADD_PATHS_EXTRAS}"
fi