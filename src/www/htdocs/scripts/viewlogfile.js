if (document.images){
  var parselimit=2
}

function UpdateDelay() {
    parselimit=document.forms[0].delayamount.value
}

function UpdateDisplay() {
    var cellObj,displayfile;

    cellObj = document.getElementById("refresh");  
    cellObj.childNodes[0].nodeValue="Updating";
    parselimit=document.forms[0].delayamount.value
    displayfile = document.getElementById("logfile").value;
    numlines = document.getElementById("numlines").value;
    makeRequest('viewlogfile.rpy?update=TRUE&displayfile=' + displayfile + "&rows=" + numlines);    
}

function beginrefresh(){
  var cellObj,displayfile;
    
  if (!document.images)
     return
  
  if (parselimit==1) {
        UpdateDisplay();  
        parselimit=document.forms[0].delayamount.value 
        setTimeout("beginrefresh()",1000);
  }
  else{ 
     parselimit-=1
     cellObj = document.getElementById("refresh"); 
     cellObj.childNodes[0].nodeValue="Refresh In : " + parselimit;
     curmin=Math.floor(parselimit/60)
     cursec=parselimit%60
     if (curmin!=0)
         curtime=curmin+" minutes and "+cursec+" seconds left until page refresh!"
     else
         curtime=cursec+" seconds left until page refresh!"
     window.status=curtime
     setTimeout("beginrefresh()",1000)
  }
}
window.onload=beginrefresh

function makeRequest(url) {
    var httpRequest;

    if (window.XMLHttpRequest) { // Mozilla, Safari, ...
        httpRequest = new XMLHttpRequest();
        if (httpRequest.overrideMimeType) {
            httpRequest.overrideMimeType('text/xml');
        }
    } 
    else if (window.ActiveXObject) { // IE
        try {
            httpRequest = new ActiveXObject("Msxml2.XMLHTTP");
        } 
        catch (e) {
            try {
                httpRequest = new ActiveXObject("Microsoft.XMLHTTP");
            } 
        catch (e) {}
        }
    }

    if (!httpRequest) {
        alert('Giving up :( Cannot create an XMLHTTP instance');
        return false;
    }
    httpRequest.onreadystatechange = function() { UpdateTable(httpRequest); };
    httpRequest.open('GET', url, true);
    httpRequest.send('');

}

function UpdateTable(httpRequest) {
    var filelist,logfile,winWidth,winHeight,loffset,toffset,nWidth,nHeight;
    
    nodls = true;
    if (httpRequest.readyState == 4) {
        if (httpRequest.status == 200) {
            logfile = document.getElementById("loglines");
            logfile.value = httpRequest.responseText;
         } else {
            alert('There was a problem with the request.');
        }
    }
}
    

    
    
