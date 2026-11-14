// Based on the xml implementation
CodeMirror.defineMode("todo", function(editorConf, config_) {
    function inText(stream, state) {
        var ch = stream.next();
        if (ch == "@" && state.seenBox) {
            stream.match(/^\s*\w*/);
            return "task_day";
        } else if (ch == "#" && state.seenBox) {
            let tag = stream.match(/^\s*\w*-?/);
            if(tag && tag[0].includes("_"))
            {
                return "task_tag "+"tag-"+String(tag[0])+" "+"tag-"+tag[0].split("_")[0];
            }
            else
            { 
                return "task_tag "+"tag-"+String(tag[0]); }
            } 
        }
    
    return {
        startState: function(baseIndent) {
            var state = {tokenize: inText,
                        inBox: false, seenBox: false}
            return state
        },
        token: function(stream, state) {

            if (stream.sol()) {
                state.seenBox = false;
            }

            if (stream.peek() === "#" && stream.column() == 0) {
                stream.next();
                const chr = stream.next();
                if(chr == ">"){
                    if(stream.next() == ">"){
                    stream.skipToEnd();
                    return "comment heading2";
                    }
                    stream.skipToEnd();
                    return "comment heading";
                } else if (chr == "!") {
                    stream.skipToEnd();
                    return "options"
                }
                stream.skipToEnd();
                return "comment";
            }

            if (stream.match(/^\s*\[x\]/) || stream.match(/^\s*\[\/\]/)){
                state.inBox = true;
                state.inBoxLine = stream.pos;
                state.seenBox = true;
                return "head";
            }

            if(stream.match(/^\s*\[ \]/) || stream.match(/^\s*\[w\]/))
            {
                state.seenBox = true;
            }

            if(state.inBox){
                stream.eatSpace();
                //var style = state.tokenize(stream, state)
                stream.skipToEnd(); //BUG: Isto impede os outros de funcionarem
                state.inBox = false;
                return "task_done";
            }

            if (!state.seenBox) {
                stream.eatSpace();
                stream.skipToEnd();
                return "err";
            }

            // match urls -- adapted from codemirror gfm mode
            // https://github.com/codemirror/codemirror5/blob/24ee74bbf433e8d484097a6ea421818a621ca13c/mode/gfm/gfm.js#L14
            if (stream.match(urlRE) &&
                stream.string.slice(stream.start - 2, stream.start) != "](" &&
                (stream.start == 0 || /\W/.test(stream.string.charAt(stream.start - 1)))) {
                        return "link";
            }

            if (stream.eatSpace()) return null;
            var style = state.tokenize(stream, state);
            return style;
        }
    }
});


CodeMirror.defineMode("todocss", function(config, parserConfig) {
    var todoMode = CodeMirror.getMode(config, "todo");
    var cssMode = CodeMirror.getMode(config, "css");
    return {
        startState: function() {
            return {
                todoState: CodeMirror.startState(todoMode),
                cssState: CodeMirror.startState(cssMode)
            }
        },
        token: function(stream, state) {

            const line = stream.string;
            const hasInlineStyle = line.includes("<style>") && line.includes("</style>");

            if (hasInlineStyle) {
                if (stream.match(/^<style>/, true)) {
                    return "tag";
                }

                // If currently inside a CSS section on the same line
                if (!stream.sol() && !stream.match(/<\/style>/, false) && stream.string.includes("<style>")) {
                    const cssStyle = cssMode.token(stream, state.cssState);
                    if (stream.match(/<\/style>/, false)) return cssStyle; // Stop before closing tag
                    return cssStyle;
                }

                if (stream.match(/<\/style>/, true)) {
                    return "tag";
                }
            }

            return todoMode.token(stream, state.todoState);
        },
        innerMode: function(state) {
            return { state: state.todoState, mode: todoMode };
        }
    }
});

var urlRE = /^((?:(?:aaas?|about|acap|adiumxtra|af[ps]|aim|apt|attachment|aw|beshare|bitcoin|bolo|callto|cap|chrome(?:-extension)?|cid|coap|com-eventbrite-attendee|content|crid|cvs|data|dav|dict|dlna-(?:playcontainer|playsingle)|dns|doi|dtn|dvb|ed2k|facetime|feed|file|finger|fish|ftp|geo|gg|git|gizmoproject|go|gopher|gtalk|h323|hcp|https?|iax|icap|icon|im|imap|info|ipn|ipp|irc[6s]?|iris(?:\.beep|\.lwz|\.xpc|\.xpcs)?|itms|jar|javascript|jms|keyparc|lastfm|ldaps?|magnet|mailto|maps|market|message|mid|mms|ms-help|msnim|msrps?|mtqp|mumble|mupdate|mvn|news|nfs|nih?|nntp|notes|oid|opaquelocktoken|palm|paparazzi|platform|pop|pres|proxy|psyc|query|res(?:ource)?|rmi|rsync|rtmp|rtsp|secondlife|service|session|sftp|sgn|shttp|sieve|sips?|skype|sm[bs]|snmp|soap\.beeps?|soldat|spotify|ssh|steam|svn|tag|teamspeak|tel(?:net)?|tftp|things|thismessage|tip|tn3270|tv|udp|unreal|urn|ut2004|vemmi|ventrilo|view-source|webcal|wss?|wtai|wyciwyg|xcon(?:-userid)?|xfire|xmlrpc\.beeps?|xmpp|xri|ymsgr|z39\.50[rs]?):(?:\/{1,3}|[a-z0-9%])|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}\/)(?:[^\s()<>]|\([^\s()<>]*\))+(?:\([^\s()<>]*\)|[^\s`*!()\[\]{};:'".,<>?«»“”‘’]))/i
