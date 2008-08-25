function init(){
    inputTracker = new Bs_Slider();
    inputTracker.attachOnChange(onInputTrackerChange);
    inputTracker.attachOnSlideStart(onInputTrackerScrollStart);
    inputTracker.attachOnSlideEnd(onInputTrackerScrollEnd);
    inputTracker.width         = 530 ;
    inputTracker.height        = 15;
    inputTracker.minVal        = 0.0;
    inputTracker.maxVal        = -1.0;
    inputTracker.valueDefault  = 0.0;
    inputTracker.valueInterval = 1/530;
    inputTracker.setDisabled(true);
    inputTracker.imgDir   = 'videolan/img/';
    inputTracker.setBackgroundImage('horizontal_background.gif', 'repeat');
    inputTracker.setArrowIconLeft('horizontal_backgroundLeft.gif', 2, 19);
    inputTracker.setArrowIconRight('horizontal_backgroundRight.gif', 2, 19);
    inputTracker.setSliderIcon('horizontal_knob.gif', 15, 19);
    inputTracker.useInputField = 0;
    inputTracker.draw('inputTrackerDiv');

    if( navigator.appName.indexOf("Microsoft Internet")==-1 )
    {
        onVLCPluginReady()
    }
    else if( document.readyState == 'complete' )
    {
        onVLCPluginReady();
    }
    else
    {
        /* Explorer loads plugins asynchronously */
        document.onreadystatechange=function() {
            if( document.readyState == 'complete' )
            {
                onVLCPluginReady();
            }
        }
    }
}

function getVLC(name)
{
    if (window.document[name]) 
    {
        return window.document[name];
    }
    if (navigator.appName.indexOf("Microsoft Internet")==-1)
    {
        if (document.embeds && document.embeds[name])
            return document.embeds[name]; 
    }
    else // if (navigator.appName.indexOf("Microsoft Internet")!=-1)
    {
        return document.getElementById(name);
    }
}
function onVLCPluginReady()
{
    updateVolume(0);
};

