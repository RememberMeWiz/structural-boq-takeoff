class DXFExtractor:
    def __init__(self, entities):
        self.entities = entities

    @staticmethod
    def get_layer(entity):
        for c, v in entity:
            if c == 8:
                return v
        return None

    def extract_text(self, target_layers=None):
        """Extracts TEXT and MTEXT entities. Returns list of dicts: {layer, text, x, y}"""
        out = []
        for e in self.entities:
            etype = e[0][1]
            if etype not in ('TEXT', 'MTEXT'):
                continue
            layer = self.get_layer(e)
            if target_layers and layer not in target_layers:
                continue
            
            x = y = None
            text = None
            for c, v in e[1:]:
                if c == 10 and x is None:
                    x = float(v)
                if c == 20 and y is None:
                    y = float(v)
                if c == 1 and text is None:
                    text = v
            out.append({'layer': layer, 'text': text, 'x': x, 'y': y})
        return out

    def extract_segments(self, target_layers=None):
        """Extracts segments from LINE and LWPOLYLINE. Returns list of dicts: {layer, p1: (x,y), p2: (x,y)}"""
        out = []
        for e in self.entities:
            etype = e[0][1]
            if etype not in ('LINE', 'LWPOLYLINE'):
                continue
            layer = self.get_layer(e)
            if target_layers and layer not in target_layers:
                continue
            
            if etype == 'LINE':
                x1 = y1 = x2 = y2 = None
                for c, v in e[1:]:
                    if c == 10: x1 = float(v)
                    if c == 20: y1 = float(v)
                    if c == 11: x2 = float(v)
                    if c == 21: y2 = float(v)
                if None not in (x1, y1, x2, y2):
                    out.append({'layer': layer, 'p1': (x1, y1), 'p2': (x2, y2)})
            elif etype == 'LWPOLYLINE':
                pts = []
                curx = None
                for c, v in e[1:]:
                    if c == 10:
                        curx = float(v)
                    if c == 20:
                        pts.append((curx, float(v)))
                # Extract segment pairs
                for i in range(len(pts) - 1):
                    out.append({'layer': layer, 'p1': pts[i], 'p2': pts[i+1]})
        return out
