# from qgis.core import *
# from qgis.utils import QGis


def getLayerStyle(layer, sln):
    renderer = layer.rendererV2()
    layer_alpha = layer.layerTransparency()
    style = ""
    if (isinstance(renderer, QgsSingleSymbolRendererV2) or
            isinstance(renderer, QgsRuleBasedRendererV2)):
        if isinstance(renderer, QgsRuleBasedRendererV2):
            symbol = renderer.rootRule().children()[0].symbol()
        else:
            symbol = renderer.symbol()
        style = """
        function style_%s(feature) {
            return %s;
        }""" % sln, getSymbolAsStyle(symbol, layer_alpha)
    elif isinstance(renderer, QgsCategorizedSymbolRendererV2):
        classAttr = handleHiddenField(layer, renderer.classAttribute())
        style = """
        function style_%s(feature) {
            switch(feature.properties['%s']) {""" % sln, classAttr
        for cat in renderer.categories():
            style += """
                case '%s':
                    return %s;
                    break;""" % (cat.value(), getSymbolAsStyle(
                                    cat.symbol(), layer_alpha))
        style += """
            }
        };"""
    elif isinstance(renderer, QgsGraduatedSymbolRendererV2):
        classAttr = handleHiddenField(layer, renderer.classAttribute())
        style = """
        function style_%s(feature) {
            switch(feature.properties['%s']) {""" % sln, classAttr
        for ran in renderer.ranges():
            style += """
            if (feature.properties['%(a)s'] > %(l)f && feature.properties['%(a)s'] < %(u)f ) {
                return %(s)s;
                break;""" % {"s": classAttr, "l": ran.lowerValue(),
                             "u": ran.upperValue(), "s": getSymbolAsStyle(
                                    cat.symbol(), layer_alpha)}
        style += """
            }
        };"""
    else:
        style = ""


def getSymbolAsStyle(symbol, stylesFolder, layer_transparency):
    styles = []
    if layer_transparency == 0:
        alpha = symbol.alpha()
    else:
        alpha = 1-(layer_transparency / float(100))
    for i in xrange(symbol.symbolLayerCount()):
        sl = symbol.symbolLayer(i)
        props = sl.properties()
        if isinstance(sl, QgsSimpleMarkerSymbolLayerV2):
            color = getRGBAColor(props["color"], alpha)
            borderColor = getRGBAColor(props["outline_color"], alpha)
            borderWidth = props["outline_width"]
            size = symbol.size() * 2
            style = "image: %s" % getCircle(color, borderColor, borderWidth,
                                            size, props)
        elif isinstance(sl, QgsSvgMarkerSymbolLayerV2):
            path = os.path.join(stylesFolder, os.path.basename(sl.path()))
            svg = xml.etree.ElementTree.parse(sl.path()).getroot()
            svgWidth = svg.attrib["width"]
            svgWidth = re.sub("px", "", svgWidth)
            svgHeight = svg.attrib["height"]
            svgHeight = re.sub("px", "", svgHeight)
            if symbol.dataDefinedAngle().isActive():
                if symbol.dataDefinedAngle().useExpression():
                    rot = "0"
                else:
                    rot = "feature.get("
                    rot += symbol.dataDefinedAngle().expressionOrField()
                    rot += ") * 0.0174533"
            else:
                rot = unicode(sl.angle() * 0.0174533)
            shutil.copy(sl.path(), path)
            style = ("image: %s" %
                     getIcon("styles/" + os.path.basename(sl.path()),
                             sl.size(), svgWidth, svgHeight, rot))
        elif isinstance(sl, QgsSimpleLineSymbolLayerV2):

            # Check for old version
            if 'color' in props:
                color = getRGBAColor(props["color"], alpha)
            else:
                color = getRGBAColor(props["line_color"], alpha)

            if 'width' in props:
                line_width = props["width"]
            else:
                line_width = props["line_width"]

            if 'penstyle' in props:
                line_style = props["penstyle"]
            else:
                line_style = props["line_style"]

            lineCap = sl.penCapStyle()
            lineJoin = sl.penJoinStyle()

            style = getStrokeStyle(color, line_style, line_width,
                                   lineCap, lineJoin)
        elif isinstance(sl, QgsSimpleFillSymbolLayerV2):
            fillColor = getRGBAColor(props["color"], alpha)

            # for old version
            if 'color_border' in props:
                borderColor = getRGBAColor(props["color_border"], alpha)
            else:
                borderColor = getRGBAColor(props["outline_color"], alpha)

            if 'style_border' in props:
                borderStyle = props["style_border"]
            else:
                borderStyle = props["outline_style"]

            if 'width_border' in props:
                borderWidth = props["width_border"]
            else:
                borderWidth = props["outline_width"]

            try:
                lineCap = sl.penCapStyle()
                lineJoin = sl.penJoinStyle()
            except:
                lineCap = 0
                lineJoin = 0

            style = ('''%s %s''' %
                     (getStrokeStyle(borderColor, borderStyle, borderWidth,
                                     lineCap, lineJoin),
                      getFillStyle(fillColor, props)))
        else:
            style = ""
        styles.append('''new ol.style.Style({
        %s
    })''' % style)
    return "[ %s]" % ",".join(styles)


def getCircle(color, borderColor, borderWidth, size, props):
    return ("""new ol.style.Circle({radius: %s + size,
            %s %s})""" %
            (size,
             getStrokeStyle(borderColor, "", borderWidth, 0, 0),
             getFillStyle(color, props)))


def getIcon(path, size, svgWidth, svgHeight, rot):
    size = math.floor(float(size) * 3.8)
    anchor = size / 2
    scale = unicode(float(size)/float(svgWidth))
    return '''new ol.style.Icon({
                  imgSize: [%(w)s, %(h)s],
                  scale: %(scale)s,
                  anchor: [%(a)d, %(a)d],
                  anchorXUnits: "pixels",
                  anchorYUnits: "pixels",
                  rotation: %(rot)s,
                  src: "%(path)s"
            })''' % {"w": svgWidth, "h": svgHeight,
                     "scale": scale, "rot": rot,
                     "s": size, "a": anchor,
                     "path": path.replace("\\", "\\\\")}


def getStrokeStyle(color, dashed, width, linecap, linejoin):
    if dashed == "no":
        return ""
    width = math.floor(float(width) * 3.8)
    dash = dashed.replace("dash", "10,5")
    dash = dash.replace("dot", "1,5")
    dash = dash.replace("solid", "")
    dash = dash.replace(" ", ",")
    dash = "[%s]" % dash
    if dash == "[]" or dash == "[no]":
        dash = "null"
    capString = "round"
    if linecap == 0:
        capString = "butt"
    if linecap == 16:
        capString = "square"
    joinString = "round"
    if linejoin == 0:
        joinString = "miter"
    if linejoin == 64:
        joinString = "bevel"
    strokeString = ("stroke: new ol.style.Stroke({color: %s, lineDash: %s, " %
                    (color, dash))
    strokeString += ("lineCap: '%s', lineJoin: '%s', width: %d})," %
                     (capString, joinString, width))
    return strokeString


def getFillStyle(color, props):
    try:
        if props["style"] == "no":
            return ""
    except:
        pass
    return "fill: new ol.style.Fill({color: %s})" % color