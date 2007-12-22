var prevState = 0;
var monitorTimerId = 0;
var inputTrackerScrolling = false;
var inputTrackerIgnoreChange = false;

function updateVolume(deltaVol)
{
    var vlc = getVLC("vlc");
    vlc.audio.volume += deltaVol;
    document.getElementById("volumeTextField").innerHTML = vlc.audio.volume+"%";
};
function formatTime(timeVal)
{
    var timeHour = Math.round(timeVal / 1000);
    var timeSec = timeHour % 60;
    if( timeSec < 10 )
        timeSec = '0'+timeSec;
    timeHour = (timeHour - timeSec)/60;
    var timeMin = timeHour % 60;
    if( timeMin < 10 )
        timeMin = '0'+timeMin;
    timeHour = (timeHour - timeMin)/60;
    if( timeHour > 0 )
        return timeHour+":"+timeMin+":"+timeSec;
    else
        return timeMin+":"+timeSec;
};
function monitor()
{
    var vlc = getVLC("vlc");
    if( vlc.log.messages.count > 0 )
    {
        // there is one or more messages in the log
        var iter = vlc.log.messages.iterator();
        while( iter.hasNext )
        {
            var msg = iter.next();
            var msgtype = msg.type.toString();
            if( (msg.severity == 1) && (msgtype == "input") )
            {
                alert( msg.message );
            }
        }
        // clear the log once finished to avoid clogging
        vlc.log.messages.clear();
    }
    var newState = vlc.input.state;
    if( prevState != newState )
    {
        if( newState == 0 )
        {
            // current media has stopped 
            onStop();
        }
        else if( newState == 1 )
        {
            // current media is openning/connecting
            onOpen();
        }
        else if( newState == 2 )
        {
            // current media is buffering data
            onBuffer();
        }
        else if( newState == 3 )
        {
            // current media is now playing
            onPlay();
        }
        else if( vlc.input.state == 4 )
        {
            // current media is now paused
            onPause();
        }
        prevState = newState;
    }
    else if( newState == 3 )
    {
        // current media is playing
        onPlaying();
    }
    if( ! monitorTimerId )
    {
        monitorTimerId = setInterval("monitor()", 1000);
    }
};

/* actions */

var aspectRatio="default";

function doChangeAspectRatio(arValue)
{
    var vlc = getVLC("vlc");
    if( vlc.input.state && vlc.input.hasVout )
    {
        vlc.video.aspectRatio = arValue;
    }
    aspectRatio = arValue;
};
function doGo(targetURL)
{
    var vlc = getVLC("vlc");
    var options = new Array(":aspect-ratio="+aspectRatio);
    vlc.playlist.items.clear();
    while( vlc.playlist.items.count > 0 )
    {
        // clear() may return before the playlist has actually been cleared
        // just wait for it to finish its job
    }
    var itemId = vlc.playlist.add(targetURL, null, options);
    if( itemId != -1 )
    {
        // clear the message log and enable error logging
        vlc.log.verbosity = 1;
        vlc.log.messages.clear();
        // play MRL
        vlc.playlist.playItem(itemId);
        if( monitorTimerId == 0 )
        {
            monitor();
        }
    }
    else
    {
        // disable log
        vlc.log.verbosity = -1;
        alert("cannot play at the moment !");
    }
};
function doPlayOrPause()
{
    var vlc = getVLC("vlc");
    if( vlc.playlist.isPlaying )
    {
        vlc.playlist.togglePause();
    }
    else if( vlc.playlist.items.count > 0 )
    {
        // clear the message log and enable error logging
        vlc.log.verbosity = 1;
        vlc.log.messages.clear();
        vlc.playlist.play();
        monitor();
    }
    else
    {
        // disable log
        vlc.log.verbosity = -1;
        alert('nothing to play !');
    }
};
function doStop()
{
    getVLC("vlc").playlist.stop();
    if( monitorTimerId != 0 )
    {
        clearInterval(monitorTimerId);
        monitorTimerId = 0;
    }
    onStop();
};
function doPlaySlower()
{
    var vlc = getVLC("vlc");
    vlc.input.rate = vlc.input.rate / 2;
};
function doPlayFaster()
{
    var vlc = getVLC("vlc");
    vlc.input.rate = vlc.input.rate * 2;
};

/* events */

function onOpen()
{
    document.getElementById("info").innerHTML = "Opening...";
    document.getElementById("PlayOrPause").disabled = true;
    document.getElementById("Stop").disabled = false;
};
function onBuffer()
{
    document.getElementById("info").innerHTML = "Buffering...";
    document.getElementById("PlayOrPause").disabled = true;
    document.getElementById("Stop").disabled = false;
};
function onPlay()
{
    document.getElementById("PlayOrPause").value = "Pause";
    document.getElementById("PlayOrPause").disabled = false;
    document.getElementById("Stop").disabled = false;
    onPlaying();
};
var liveFeedText = new Array("Live", "((Live))", "(( Live ))", "((  Live  ))");
var liveFeedRoll = 0;
function onPlaying()
{
    if( ! inputTrackerScrolling )
    {
        var vlc = getVLC("vlc");
        var info = document.getElementById("info");
        var mediaLen = vlc.input.length;
        inputTrackerIgnoreChange  = true;
        if( mediaLen > 0 )
        {
            // seekable media
            if( inputTracker.maxVal != 1.0 )
            {
                document.getElementById("PlayOrPause").disabled = false;
                inputTracker.setDisabled(false);
                inputTracker.maxVal = 1.0;
            }
            inputTracker.setValue(vlc.input.position);
            info.innerHTML = formatTime(vlc.input.time)+"/"+formatTime(mediaLen);
        }
        else
        {
            // non-seekable "live" media
            if( inputTracker.maxVal != 0.0 )
            {
                document.getElementById("PlayOrPause").disabled = true;
                inputTracker.maxVal = 0.0;
                inputTracker.setValue(0.0);
                inputTracker.setDisabled(true);
            }
            liveFeedRoll = liveFeedRoll & 3;
            info.innerHTML = liveFeedText[liveFeedRoll++];
        }
        inputTrackerIgnoreChange  = false;
    }
};
function onPause()
{
    document.getElementById("PlayOrPause").value = " Play ";
};
function onStop()
{
    var vlc = getVLC("vlc");
    // disable logging
    vlc.log.verbosity = -1;
    document.getElementById("Stop").disabled = true;
    if( ! inputTracker.disabled )
    {
        inputTrackerIgnoreChange  = true;
        inputTracker.setValue(0.0);
        inputTracker.setDisabled(true);
        inputTracker.maxVal = 0.0;
        inputTrackerIgnoreChange  = false;
    }
    document.getElementById("info").innerHTML = "-:--:--/-:--:--";
    document.getElementById("PlayOrPause").value = " Play ";
    document.getElementById("PlayOrPause").disabled = false;
};
function onInputTrackerScrollStart()
{
    inputTrackerScrolling = true;
};
function onInputTrackerScrollEnd(inputTracker, value, pos)
{
    inputTrackerScrolling = false;
};
function onInputTrackerChange(inputTracker, value, pos)
{
    if( ! inputTrackerIgnoreChange )
    {
        var vlc = getVLC("vlc");
        if( (vlc.input.state == 3) && (vlc.input.position != value) )
        {
            var info = document.getElementById("info");
            vlc.input.position = value;
            info.innerHTML = formatTime(vlc.input.time)+"/"+formatTime(vlc.input.length);
        }
    }
};

