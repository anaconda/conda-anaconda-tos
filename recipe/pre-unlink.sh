#!/bin/sh

_PREFIX="${CONDA_PREFIX:-${PREFIX:-}}"
_PYTHON="${_PREFIX}/python.exe"
[ -f "${_PYTHON}" ] || _PYTHON="${_PREFIX}/bin/python"
"${_PYTHON}" -m conda tos clean --all >>"${_PREFIX}/.messages.txt" 2>&1 || :
