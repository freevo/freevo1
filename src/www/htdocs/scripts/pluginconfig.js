function DisplayList(listname) {
    var list;
    
    list = document.getElementById(listname)
    if (list.style.display == "none")
        list.style.display = "";
    else 
        list.style.display = "none";
}

function CreateSetting(setting_name) {
    var configfile,updateurl;
    
    configfile =document.getElementById('configfile').value

    updateurl = 'configedit.rpy?configfile=' + configfile + '&cmd=UPDATE&udname=' + setting_name + '&udvalue=New&udenable=FALSE';
    updateurl = updateurl + '&startline=-1&endline=-1&syntaxcheck=FALSE';
    makeRequest(updateurl, setting_name);
}

function GetPluginVars(pname) {
    var vr,cnt,vrctrl;
    var varlist = [];
    
    cnt =0
    vrctrl =  document.getElementById(pname + "_var" + cnt);
    
    while (vrctrl != null) {
        vr = [vrctrl.name, vrctrl.value]
        varlist[cnt] = vr
        cnt++;
        vrctrl =  document.getElementById(pname + "_var" + cnt);
    }
    return varlist;
}

function UpdatePlugin(pname) {
    var cmd,lineno,url,varlist,level_ctrl;
 
    varlist = GetPluginVars(pname);
    cmd = document.getElementById(pname + "_cmd").value;
    lineno = document.getElementById(pname + "_lineno").value;
    url = "configedit.rpy?cmd=PLUGINUPDATE&pluginaction=" + cmd + "&pluginname=" + pname + "&pluginline=" + lineno;

    // Check to see if plugin has level control.
    level_ctrl = document.getElementById(pname + '_level')
    if (level_ctrl) {
        url = url + '&level='  + level_ctrl.value
    }


    makeRequest(url , pname);
}

function UpdateStatus(hRequest,cname) {
    var cell;

    if (hRequest.readyState == 4) {
        if (hRequest.status == 200) {
            cell = document.getElementById(cname + "_config_line");
            cell.innerHTML = hRequest.responseText;
           
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


