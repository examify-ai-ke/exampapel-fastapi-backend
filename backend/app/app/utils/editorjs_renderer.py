from typing import Dict, Any, List

def render_editorjs(data: Dict[str, Any]) -> str:
    """
    Converts Editor.js JSON data to HTML string.
    """
    if not isinstance(data, dict) or "blocks" not in data:
        # Fallback for simple string or invalid data
        return str(data) if data else ""

    html_output = []
    
    for block in data.get("blocks", []):
        block_type = block.get("type")
        content = block.get("data", {})
        
        if block_type == "header":
            level = content.get("level", 2)
            text = content.get("text", "")
            html_output.append(f"<h{level}>{text}</h{level}>")
            
        elif block_type == "paragraph":
            text = content.get("text", "")
            html_output.append(f"<p>{text}</p>")
            
        elif block_type == "list":
            style = content.get("style", "unordered")
            items = content.get("items", [])
            tag = "ol" if style == "ordered" else "ul"
            list_items = "".join([f"<li>{item}</li>" for item in items])
            html_output.append(f"<{tag}>{list_items}</{tag}>")
            
        elif block_type == "table":
            with_headings = content.get("withHeadings", False)
            rows = content.get("content", [])
            
            table_html = "<table class='editorjs-table'>"
            
            for i, row in enumerate(rows):
                table_html += "<tr>"
                for cell in row:
                    tag = "th" if with_headings and i == 0 else "td"
                    table_html += f"<{tag}>{cell}</{tag}>"
                table_html += "</tr>"
                
            table_html += "</table>"
            html_output.append(table_html)
            
        elif block_type == "delimiter":
            html_output.append("<div class='editorjs-delimiter'>***</div>")
            
        elif block_type == "image":
            url = content.get("file", {}).get("url", "")
            caption = content.get("caption", "")
            with_border = content.get("withBorder", False)
            with_background = content.get("withBackground", False)
            stretched = content.get("stretched", False)
            
            classes = []
            if with_border: classes.append("with-border")
            if with_background: classes.append("with-background")
            if stretched: classes.append("stretched")
            
            class_str = " ".join(classes)
            
            img_html = f"<div class='editorjs-image {class_str}'>"
            if url:
                img_html += f"<img src='{url}' alt='{caption}' />"
            if caption:
                img_html += f"<div class='caption'>{caption}</div>"
            img_html += "</div>"
            html_output.append(img_html)

        elif block_type == "code":
             code = content.get("code", "")
             html_output.append(f"<pre><code class='editorjs-code'>{code}</code></pre>")

        elif block_type == "quote":
            text = content.get("text", "")
            caption = content.get("caption", "")
            alignment = content.get("alignment", "left")
            html_output.append(f"<blockquote class='editorjs-quote {alignment}'>{text}<footer>{caption}</footer></blockquote>")
            
    return "".join(html_output)
