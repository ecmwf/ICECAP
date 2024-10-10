#!/bin/ksh
#SBATCH --job-name=%ECF_NAME%
#SBATCH --qos=nf
#SBATCH --time=24:00:00
#SBATCH --output=%ECF_JOBOUT%
#SBATCH --error=%ECF_JOBOUT%
#SBATCH --mem=128GB


# Define an error handler
ERROR() {
   # clear -x flag, we do not echo script lines from in here
   set -x
   # Clear -e flag, so we don't fail
   set +e
   # print error message
   errmsg="$2"
   if [ $1 -eq 0 ]; then
       errmsg="CANCELLED or TIMED OUT"
   fi
   ecflow_client --abort="$errmsg"
   trap - 0 $SIGNAL_LIST   # Remove the traps
   # End the script
   if [ $1 -eq 0 ]; then
       exit -1
   else
       exit $1
   fi
}

# Trap any signal that may cause the script to fail
# Note: don't trap SIGTERM/SIGCONT for Slurm to properly reach shell children on cancel/timeout
export SIGNAL_LIST='1 2 3 4 5 6 7 8 10 11 13 24 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64'

for signal in $SIGNAL_LIST; do
  trap "ERROR $signal \"Signal $(kill -l $signal) ($signal) received \"" $signal
done

# Trap any calls to exit and errors caught by the -e flag
trap "ERROR \$? \"EXIT code \$?\"" 0

set -x # echo script lines as they are executed
set -e # stop the shell on first error
set -u # fail when using an undefined variable
set -o pipefail # If any command in a pipeline fails, that return code will be used as the return code of the whole pipeline

# Defines the variables that are needed for any communication with ECF
export ECF_PORT=%ECF_PORT%    # The server port number
export ECF_HOST=%ECF_HOST%    # The name of ecf host that issued this task
export ECF_NAME=%ECF_NAME%    # The name of this current task
export ECF_PASS=%ECF_PASS%    # A unique password
export ECF_TRYNO=%ECF_TRYNO%  # Current try number of the task
export ECF_RID=${SLURM_JOB_ID:-$$}
export ECF_PYTHON=%ECF_PYTHON%

module load ecflow/%ECF_VERSION%

# To allow personal conda environments
if [ $ECF_PYTHON == 'None' ]; then
    cd %ETCDIR%
    source ./load_modules python3 ecmwf-toolbox
    export ECF_PYTHON=python3
else
    # see https://github.com/ks905383/xagg/issues/47
    esmf_file=$($ECF_PYTHON -c "import os; from pathlib import Path; print(str(Path(os.__file__).parent.parent / 'esmf.mk'))")
    export ESMFMKFILE=$esmf_file
fi

# Tell ecFlow we have started
ecflow_client --init=$ECF_RID

