// Based on the xml implementation
CodeMirror.defineMode("todo", function(editorConf, config_) {
    function inText(stream, state) {
        var ch = stream.next();
        if (ch == "@" && state.seenBox) {
            stream.match(/^\s*\w*/);
            return "task_day";
        } else if (ch == "#" && state.seenBox) {
            let tag = stream.match(/^\s*\w*/);
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
                if(stream.next() == ">"){
                    if(stream.next() == ">"){
                    stream.skipToEnd();
                    return "comment heading2";
                    }
                    stream.skipToEnd();
                    return "comment heading";
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