function Detect_Channels(control_name) {
    var updateurl;

    url = ''
    startline = document.getElementById(control_name + "_startline").value
    endline = document.getElementById(control_name + "_endline").value
    div_enable = document.getElementById(control_name + '_enable')
    
    configfile =document.getElementById('configfile').value
    updateurl = 'configedit.rpy?configfile=' + configfile + '&cmd=DETECT_CHANNELS&udenable=FALSE';
    updateurl = updateurl + "&startline=" + startline + '&endline=' + endline;
   
    makeRequest(updateurl,control_name,control_name + "_fileline");

}


function PrepareFileList(cname) {
    var cvalue,tblabel,tbfile,cnt;
    var line;

    cvalue = ""
    tblabel = document.getElementById(cname + "_label0")
    tbfile = document.getElementById(cname + "_file0")

    cnt = 0
    while (tblabel != null ) {
        // If the current line is hidden then skip it.
        line = document.getElementById(cname + '_line_' + cnt)
        if (line.style.display == "") {

        
            if (tblabel.value != "") {
                if (tbfile != null)
                    cvalue = cvalue + "('" +  tblabel.value  + "','" + tbfile.value + "'),";
                else
                    cvalue = cvalue + "'" + tblabel.value + "',"
            }
        }
        cnt++;
        tblabel = document.getElementById(cname + "_label"+cnt)
        tbfile = document.getElementById(cname + "_file"+cnt)
    }
        
    cvalue = "[" + cvalue.substring(0,cvalue.length -1) + "]";
    return cvalue;
}


function PrepareDictionary(cname) {
    var cvalue,tblabel,tbfile,cnt;
    var line;

    cvalue = ""
    tblabel = document.getElementById(cname + "_key0")
    tbfile = document.getElementById(cname + "_value0")

    cnt = 0
    while (tblabel != null ) {

        // If the current line is hidden then skip it.
        line = document.getElementById(cname + '_line_' + cnt)
        if (line.style.display == "") {

            if (tblabel.value != "") {
                if (tbfile != null)
                    cvalue = cvalue + "'" +  tblabel.value  + "': '" + tbfile.value + "',";
                else
                    cvalue = cvalue + "'" + tblabel.value + "',"
            }
        }
        cnt++;
        tblabel = document.getElementById(cname + "_key"+cnt)
        tbfile = document.getElementById(cname + "_value"+cnt)
    }
    
    cvalue = "{" + cvalue.substring(0,cvalue.length -1) + "}";

    return cvalue;
}


function ShowList(cname) {
    var list, anchor;

    list = document.getElementById(cname + '_list')
    anchor = document.getElementById(cname + '_anchor')

    if (list.style.display == "")  {
        list.style.display = "none";
        anchor.className = 'Setting_Line_Close';
    }
    else {
       list.style.display = "";
        anchor.className = 'Setting_Line_Open';
    }
}

function MoveTVChannel(cname,crow,cmove) {
    var tvalue,svalue,dvalue,drow;
    
    drow = crow + cmove
    dvalue = document.getElementById(cname + '_item' + drow)
    if (dvalue == null) 
        return
    
    tvalue = dvalue.value
    dvalue.value = document.getElementById(cname + '_item'  + crow).value 
    document.getElementById(cname + '_item' +  crow).value = tvalue    
    document.getElementById(cname + "_btn_update").style.display = ""

}

function PrepareChannelList(cname) {
    var cvalue, tblabel,cnt;

    cvalue = "["
    tblabel = document.getElementById(cname + "_item0")
    cnt = 0
    while (tblabel != null ) {
        if (tblabel.value != "")
            cvalue = cvalue + "" +  tblabel.value  + ",";
        cnt++;
        tblabel = document.getElementById(cname + "_item" + cnt )
    }
    
    cvalue =  cvalue.substring(0,cvalue.length -1) + "]";
    return cvalue;
}

function GetListLine(cname,row) {
    var tblcell,line;


    // If the current line is hidden then skip it.
    line = document.getElementById(cname + '_line' + row)
    cline = ""
    if (line.style.display == "") {
        // Loop throught all of the cols
        ccnt = 0
        column_cnt = 0
        tblcell = document.getElementById(cname + '_item' + row + ccnt)
        while (tblcell != null) {
            if (tblcell.value != "")
                start_char = "'"
            end_char = "'"
            schar = tblcell.value.charAt(0);
            echar = tblcell.value.charAt(tblcell.value.length - 1)
            if (schar == "(")
                start_char = "";
            if (echar == ")")
                end_char = "";

            tb_value = tblcell.value;
            curcell = start_char +  tb_value + end_char
            if (curcell != "''") {
                cline =  cline + curcell + ",";
                column_cnt++;
            }
            
            ccnt++;
            tblcell = document.getElementById(cname + "_item" + row + ccnt)
        }
    }
    return cline
}


function PrepareItemList(cname) {
    var rcnt,ccnt,cvalue,tblcell,start_char,end_char;
    var cline,curcell, column_cnt, tb_value;
    
    cvalue = ""
    tblcell = document.getElementById(cname + "_item00")
    rcnt = 0
    
    // Loop throught all of the rows.
    while (tblcell != null )  {
        cvalue = cvalue + GetListLine(cname, rcnt)
        rcnt++;
        ccnt = 0
        if (column_cnt > 0)
            cvalue = cvalue + '(' + cline.substring(0,cline.length -1) + '),';
        // Get the fist control on the next line.
        tblcell = document.getElementById(cname + "_item" + rcnt + ccnt);
    }
    
    if (cvalue != "") 
        cvalue = "[" + cvalue.substring(0,cvalue.length -1) + "]";

    return cvalue;
}


function UpdateStatus(hRequest,cname,cstatus) {
    var cell,btnUpdate,disableupdate;

    if (hRequest.readyState == 4) {
        if (hRequest.status == 200) {
           cell = document.getElementById(cstatus);
           cell.innerHTML = hRequest.responseText;
            
            btnUpdate =  document.getElementById(cname + "_btn_update") 
            
            if (cell.textContent.search("Error") == -1)
               btnUpdate.style.display = ""; 
            else
               btnUpdate.style.display = "none";

        } else {
            alert('There was a problem with the request.');
        }
    }
}

function makeRequest(url,cname,cstatus) {
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
    httpRequest.onreadystatechange = function() { UpdateStatus(httpRequest,cname,cstatus); };
    httpRequest.open('GET', url, true);
    httpRequest.send('');
}

function SaveValue(control_name,type) {
    // Get the Value from the text box. 
    var svalue,tb,chk,updateurl,strenable;
    var startline,endline, sname,div_enable;
    var other_opts,update_args;
    var string_type;

    other_opts = ''
    sname = document.getElementById(control_name + '_ctrlname').value
    svalue = GetSettingValue(control_name,type)    

    
    chk  = document.getElementById(control_name + "_chk")
    startline = document.getElementById(control_name + "_startline").value
    endline = document.getElementById(control_name + "_endline").value
    div_enable = document.getElementById(control_name + '_enable')
    
    if (chk.checked) { 
        strenable = "TRUE";
        div_enable.className = 'enablecontrol'
    } 
    else {
        strenable = "FALSE"        
        div_enable.className = 'disablecontrol'
    }
    
    configfile =document.getElementById('configfile').value;
    update_args = 'configfile=' + Url.encode(configfile);
    update_args = update_args + '&cmd=UPDATE';
    update_args = update_args + '&udname=' + sname;
    update_args = update_args + '&udvalue=' + Url.encode(svalue);
    update_args = update_args + '&udenable=' + strenable;
    update_args = update_args + '&startline=' + startline ;
    update_args = update_args + '&endline=' + endline ;
    update_args = update_args + Url.encode(other_opts);

    updateurl = 'configedit.rpy?' + update_args
    makeRequest(updateurl,control_name,control_name + "_fileline");
}

function GetSettingValue(control_name,type) {
    if (type == "tv_channels") 
        svalue = PrepareChannelList(control_name);
    
    else if (type == "fileitemlist") 
        svalue =  PrepareFileList(control_name);
    
    else if (type == "itemlist") 
        svalue = PrepareItemList(control_name);

    else if (type == "dictionary")
        svalue = PrepareDictionary(control_name);

    else if(type == 'keymap') {
        document.getElementById(control_name + '_btn_update').style.display = ''
        
        sname = 'KEYMAP[' + document.getElementById( control_name + '_key').value + ']'
        svalue = document.getElementById(control_name + '_event').value
    }
    else {
        tb = document.getElementById(control_name);
        svalue = tb.value;
        string_type = document.getElementById(control_name + '_string')
        if (string_type.value == 'True')
            svalue = "'" + svalue + "'"
    }

    return svalue
}

function CheckListLine(control_name,type,row) {
    CheckValue(control_name,type,row);
}

function CheckValue(control_name ,type,row) {
    var svalue,tb,chk,updateurl,strenable;
    var configfile,check_args;
    var string_type;

    sname = document.getElementById(control_name + '_ctrlname').value
    svalue = GetSettingValue(control_name,type)
    //alert(svalue);

    // Check the hole control.
    configfile =document.getElementById('configfile').value
    check_args = 'configfile=' + Url.encode(configfile)
    check_args = check_args + '&cmd=CHECK'
    check_args = check_args + '&udname=' + sname
    check_args = check_args + '&udvalue=' + Url.encode(svalue)

    updateurl = 'configedit.rpy?' + check_args
    if (type != 'keymap') 
        makeRequest(updateurl,control_name,control_name + "_check");
    
    // if a fileitemlist or itemitem list check to see if the lines it ok.
    
    
}


function DeleteLines(cname, sline,eline) {
     var url;   

    configfile =document.getElementById('configfile')
    url = 'configedit.rpy?configfile=' + configfile + '&cmd=DELETE&startline=' + sline + '&endline=' + eline
    makeRequest(url,cname,cname + "_line")

}


function DeleteItemLine(lineid,btnupdate) {
   var line;

   line = document.getElementById(lineid)
   line.style.display = "none";

    btnupdate = document.getElementById(btnupdate)
    btnupdate.style.display = "";

}


/**
*
* URL encode / decode
* http://www.webtoolkit.info/
*
**/

var Url = {

    // public method for url encoding
    encode : function (string) {
        return escape(this._utf8_encode(string));
    },

    // public method for url decoding
    decode : function (string) {
        return this._utf8_decode(unescape(string));
    },

    // private method for UTF-8 encoding
    _utf8_encode : function (string) {
        string = string.replace(/\r\n/g,"\n");
        var utftext = "";

        for (var n = 0; n < string.length; n++) {

            var c = string.charCodeAt(n);

            if (c < 128) {
                utftext += String.fromCharCode(c);
            }
            else if((c > 127) && (c < 2048)) {
                utftext += String.fromCharCode((c >> 6) | 192);
                utftext += String.fromCharCode((c & 63) | 128);
            }
            else {
                utftext += String.fromCharCode((c >> 12) | 224);
                utftext += String.fromCharCode(((c >> 6) & 63) | 128);
                utftext += String.fromCharCode((c & 63) | 128);
            }

        }

        return utftext;
    },

    // private method for UTF-8 decoding
    _utf8_decode : function (utftext) {
        var string = "";
        var i = 0;
        var c = c1 = c2 = 0;

        while ( i < utftext.length ) {

            c = utftext.charCodeAt(i);

            if (c < 128) {
                string += String.fromCharCode(c);
                i++;
            }
            else if((c > 191) && (c < 224)) {
                c2 = utftext.charCodeAt(i+1);
                string += String.fromCharCode(((c & 31) << 6) | (c2 & 63));
                i += 2;
            }
            else {
                c2 = utftext.charCodeAt(i+1);
                c3 = utftext.charCodeAt(i+2);
                string += String.fromCharCode(((c & 15) << 12) | ((c2 & 63) << 6) | (c3 & 63));
                i += 3;
            }

        }

        return string;
    }

}
