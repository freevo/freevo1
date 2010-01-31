#!/bin/sh

CROP="1"
TOTAL_LOOPS="10"
NICE_PRI="10"
SOURCE="$1"


######### CROP Settings #############
if [ "$CROP" == "1" ]; then
  echo "Please wait.  It make take a couple minutes to detect crop parameters."
  A=0
  while [ "$A" -lt "$TOTAL_LOOPS" ] ; do
    A="$(( $A + 1 ))"
    SKIP_SECS="$(( 35 * $A ))"
  
    nice -n $NICE_PRI nohup mplayer "$SOURCE" $CHAPTER -ss $SKIP_SECS \
     -identify -frames 20 -vo md5sum -ao null -nocache -speed 100 -noframedrop \
     -vf ${VF_OPTS}cropdetect=20:16 2>&1 > mplayer.log < /dev/null

# echo DEBUG ; cat mplayer.log
  
    CROP[$A]=`awk -F 'crop=' '/crop/ {print $2}' < mplayer.log\
     | awk -F ')' '{print $1}' | tail -n 1`

    SOURCE_AUDIORATE=`awk -F '=' '/ID_AUDIO_BITRATE/ {print $2}'<mplayer.log`

    SOURCE_LENGTH=`awk -F '=' '/ID_LENGTH/ {print $2}'<mplayer.log`
  done
  rm md5sums mplayer.log 


  B=0
  while [ "$B" -lt "$TOTAL_LOOPS" ] ; do
    B="$(( $B + 1 ))"
  
    C=0
    while [ "$C" -lt "$TOTAL_LOOPS" ] ; do
      C="$(( $C + 1 ))"
  
      if [ "${CROP[$B]}" == "${CROP[$C]}" ] ; then
        COUNT_CROP[$B]="$(( ${COUNT_CROP[$B]} + 1 ))"
      fi
    done  
  done
  
  HIGHEST_COUNT=0
  
  D=0
  while [ "$D" -lt "$TOTAL_LOOPS" ] ; do
     D="$(( $D + 1 ))"
  
       if [ "${COUNT_CROP[$D]}" -gt "$HIGHEST_COUNT" ] ; then
         HIGHEST_COUNT="${COUNT_CROP[$D]}"
         GREATEST="$D"
       fi
  done
  
  CROP="crop=${CROP[$GREATEST]}"
  
  echo -e "\n\nCrop Setting is: $CROP ... \n\n" 

else
  nice -n $NICE_PRI nohup mplayer "$SOURCE" $CHAPTER \
   -identify -frames 0 -vo md5sum -ao null -nocache \
   2>&1 > mplayer.log < /dev/null

  SOURCE_AUDIORATE=`awk -F '=' '/ID_AUDIO_BITRATE/ {print $2}'<mplayer.log`

  SOURCE_LENGTH=`awk -F '=' '/ID_LENGTH/ {print $2}'<mplayer.log`

  rm md5sums mplayer.log 
fi
