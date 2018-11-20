#
# build-package.ps1
#
# Easiest way to build is to make sure the repo is the current directory,
# then run setup.py from there.
#

$ThisFile = $MyInvocation.MyCommand.Path
$ThisFolder = Split-Path -Parent $ThisFile

Write-Host "cd $ThisFolder"
cd $ThisFolder

python setup.py sdist bdist_wheel
