function BrowseFiles(browse_area, setting_name, browse_type) {
    var browse_div, cancel_button, browse_folder, file_textbox;
    var btn_browse;
    
    browse_div = document.getElementById(browse_area + "_filebrowse")
    browse_div.style.display = "";

    cancel_button = document.getElementById(browse_area + "_cancel")
    cancel_button.style.display = "";

    btn_browse = document.getElementById(browse_area + '_browse')
    btn_browse.style.display = 'none';
    
    file_textbox = document.getElementById(browse_area);
    browse_folder = file_textbox.value;

    getFileList(browse_area ,browse_folder, setting_name, browse_type)
}

function CancelBrowse(browse_area) {
    var browse_div, cancel_button,btn_browse;

    browse_div = document.getElementById(browse_area + "_filebrowse")
    browse_div.style.display = "none";
    
    cancel_button = document.getElementById(browse_area + "_cancel")
    cancel_button.style.display = 'none';

    btn_browse = document.getElementById(browse_area + '_browse')
    btn_browse.style.display = ''
}

function getFileList(browse_area,browse_folder, setting_name, browse_type) {
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

    if (browse_type == 'D')
        url = 'configedit.rpy?cmd=BROWSEDIRECTORY&browsefile=' + browse_folder + '&browsearea=' + browse_area + '&setting_name=' + setting_name
    else
        url = 'configedit.rpy?cmd=BROWSEFILE&browsefile=' + browse_folder + '&browsearea=' + browse_area + '&setting_name=' + setting_name
 

    httpRequest.onreadystatechange = function() { UpdateFileList(httpRequest, browse_area); };
    httpRequest.open('GET', url, true);
    httpRequest.send('');
}

function UpdateFileList(hRequest,browse_area) {
    var cell,btnUpdate,disableupdate;

    if (hRequest.readyState == 4) {
        if (hRequest.status == 200) {
           cell = document.getElementById(browse_area + "_filebrowse");
           cell.innerHTML = hRequest.responseText;

        } else {
            alert('There was a problem with the request.');
        }
    }
}

function SelectFile(full_file_name,update_control) {
    var file_textbox, update_button;

    file_textbox = document.getElementById(update_control);
    file_textbox.value = full_file_name; 
    CancelBrowse(update_control)
    
    update_button=  document.getElementById(update_control + "_btn_update") 
    update_button.style.display = ""; 
    
}

