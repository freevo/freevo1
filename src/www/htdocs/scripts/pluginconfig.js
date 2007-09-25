function FilterList(cname) {
     var filter;   

     filter = document.getElementById(cname).value;
     window.location = 'config.rpy?filterlist=' + filter
}

function UpdatePlugin(pname) {
    var cmd,lineno,url;

    cmd = document.getElementById(pname + "_cmd").value;
    lineno = document.getElementById(pname + "_lineno").value;
    url = "pluginconfig.rpy?cmd=" + cmd + "&pluginname=" + pname + "&pluginline=" + lineno;
    makeRequest(url , pname);
}


function RemovePlugin(pname) {
    var lineno,url;

    // Get the Line Number of the Plugin.
    lineno = document.getElementById(pname + "_lineno").value;
    url = "pluginconfig.rpy?cmd=REMOVE&pluginname=" + pname + "&pluginline=" + lineno;
    makeRequest(url , pname);
}

function EnablePlugin(pname) {
    var lineno,url;

    // Get the Line Number of the Plugin.
    lineno = document.getElementById(pname + "_lineno").value  
    url = "pluginconfig.rpy?cmd=ACTIVATE&pluginname=" + pname + "&pluginline=" + lineno
    makeRequest(url , pname)
}

function DisablePlugin(pname) {
    var lineno,url;

    // Get the Line Number of the Plugin.
    lineno = document.getElementById(pname + "_lineno").value  
    url = "pluginconfig.rpy?cmd=DISABLE&pluginname=" + pname + "&pluginline=" + lineno
    makeRequest(url , pname)
}


function FilterListPlugin() {
     var grpfilter,statfilter;   

     grpfilter = document.getElementById('grpfilter').value;
     statfilter = document.getElementById('statfilter').value;

     window.location = 'pluginconfig.rpy?filterlist=' + grpfilter + "&pluginfilter=" + statfilter
}

function UpdateStatus(hRequest,cname) {
    var cell;

    if (hRequest.readyState == 4) {
        if (hRequest.status == 200) {
            cell = ""
//            alert(hRequest.responseText)           
        } else {
            
            alert('There was a problem with the request.');
        }
    }
}

function makeRequest(url,cname) {
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
    httpRequest.onreadystatechange = function() { UpdateStatus(httpRequest,cname); };
    httpRequest.open('GET', url, true);
    httpRequest.send('');
}

function SaveValue(sname) {
    // Get the Value from the text box. 
    var svalue,tb,chk,updateurl,strenable;
    var startline,endline;

    tb = document.getElementById(sname + "_tb")
    chk  = document.getElementById(sname + "_chk")
    startline = document.getElementById(sname + "_startline").value
    endline = document.getElementById(sname + "_endline").value
    svalue = tb.value
    strenable = "FALSE"
    if (chk.checked) 
        strenable = "TRUE"
    updateurl = 'config.rpy?update=TRUE&udname=' + sname + '&udvalue=' + svalue + '&udenable=' + strenable
    updateurl = updateurl + "&startline=" + startline + '&endline=' + endline
    
    makeRequest(updateurl,sname);
}

function DeleteValue(sname) {
    // Get the Value from the text box. 
    var svalue,tb,chk,updateurl,strenable;
    var startline,endline;

    startline = document.getElementById(sname + "_startline").value
    endline = document.getElementById(sname + "_endline").value
    svalue = tb.value
    strenable = "FALSE"
    if (chk.checked) 
        strenable = "TRUE"
    updateurl = 'config.rpy?delete=TRUE&startline=' + startline + '&endline=' + endline
//    makeRequest(updateurl);
}
