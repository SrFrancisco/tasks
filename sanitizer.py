from copy import deepcopy
import re
from typing import List, Union, cast
import nh3
import tinycss2.ast
from consts import *

CSSDeclaration = Union[
    tinycss2.ast.Declaration,
    tinycss2.ast.AtRule,
    tinycss2.ast.QualifiedRule,
    tinycss2.ast.Comment,
    tinycss2.ast.WhitespaceToken,
    tinycss2.ast.ParseError
]
CSSNode = Union[ # REF: tinycss2 Documentation
    tinycss2.ast.ParseError,
    tinycss2.ast.WhitespaceToken,
    tinycss2.ast.LiteralToken,
    tinycss2.ast.IdentToken,
    tinycss2.ast.AtKeywordToken,
    tinycss2.ast.HashToken,
    tinycss2.ast.StringToken,
    tinycss2.ast.URLToken,
    tinycss2.ast.NumberToken,
    tinycss2.ast.PercentageToken,
    tinycss2.ast.DimensionToken,
    tinycss2.ast.UnicodeRangeToken,
    tinycss2.ast.ParenthesesBlock,
    tinycss2.ast.SquareBracketsBlock,
    tinycss2.ast.CurlyBracketsBlock,
    tinycss2.ast.FunctionBlock,
    tinycss2.ast.Comment,
]

ALLOWED_TAGS = deepcopy(nh3.ALLOWED_TAGS) # REF: https://github.com/messense/nh3/issues/74
ALLOWED_TAGS.add("style")
def sanitize_html(content:str) -> str:
    return nh3.clean(html=content,      # only allows single html line
                     tags=ALLOWED_TAGS,
                     attributes={'*':{'class'}},   # need to allow classes TODO: More fine-grained
                     clean_content_tags={"script"}
                    )


def _is_sanitize_css(css:str) -> bool:
    ast:List[Union[tinycss2.parser.QualifiedRule, tinycss2.parser.AtRule, 
        tinycss2.ast.Comment, 
        tinycss2.ast.WhitespaceToken, 
        tinycss2.ast.ParseError]] = tinycss2.parse_stylesheet(css,skip_comments=True,skip_whitespace=True)
    
    # [<QualifiedRule … { … }>]
    for qualified_rule in ast:
        if qualified_rule.type == 'qualified-rule':
            decl_list:list[CSSDeclaration] = tinycss2.parse_blocks_contents(cast(tinycss2.parser.QualifiedRule, qualified_rule).content)
            for decl in decl_list:
                if decl.type == 'declaration':
                    # check rule
                    decl = cast(tinycss2.ast.Declaration, decl)
                    if(decl.lower_name not in CSS_ALLOWED_IDENT):
                        print("Decl", decl.lower_name, "not allowed!")
                        return False
                    # we now check the value
                    values = cast(list[CSSNode], decl.value)
                    for value in values:
                        if(value.type == 'error'): return False
                        if(value.type == 'url' and 'url' not in CSS_ALLOWED_FUNCTIONS):
                            return False
                        if(value.type == '{} block' or value.type == '[] block' or \
                        value.type == '() block' or value.type == 'unicode-range'):
                            return False
                        if(value.type == 'function' and \
                            cast(tinycss2.ast.FunctionBlock,value).name not in CSS_ALLOWED_FUNCTIONS):
                                print("Function not supported")
                                return False

                elif decl.type == 'at-rule':
                    return False # not supported
                elif decl.type == 'qualified-rule':
                    return False # not supported
                elif decl.type == 'error':
                    return False

        elif qualified_rule.type == 'at-rule':
            # restrict any at-rule: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_syntax/At-rules
            # this is to prevent @import
            if cast(tinycss2.ast.AtRule,qualified_rule).lower_at_keyword not in CSS_ALLOWED_AT_RULE:
                print("AT Rule not allowed")
                return False
        elif qualified_rule.type == 'error': return False
            
    return True


def sanitize_css(css_line:str):
    #return ""
    ret = re.search(r'<style>(.*?)</style>', css_line)
    if(ret != None): 
        if SANITIZE_CSS and (not _is_sanitize_css(ret.group(1))):
            print("!!! ERROR PARSING!")
            return ""  
        return re.sub(r'\.tag-(.*? )', r'.cm-tag-\1', ret.group(1))      
    else: return ""