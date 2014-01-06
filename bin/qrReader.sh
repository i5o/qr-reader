#!/bin/bash

ARCH=`uname -m`

if [ "$ARCH" == "armv7l" ]
then
    export LD_LIBRARY_PATH="$SUGAR_BUNDLE_PATH/tools/arm/lib"
elif [ "$ARCH" == "x86_64" ]
then
    export LD_LIBRARY_PATH="$SUGAR_BUNDLE_PATH/tools/64/lib"
else
    export LD_LIBRARY_PATH="$SUGAR_BUNDLE_PATH/tools/32/lib"
fi

exec sugar-activity activity.QrReader $@
