import os

class DXFParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.pairs = []
        self.entities = []

    def parse(self):
        """Parse ASCII DXF into code-value pairs."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"DXF file not found: {self.file_path}")

        with open(self.file_path, 'r', errors='ignore') as f:
            lines = f.read().split('\n')
        lines = [l.rstrip('\r') for l in lines]

        self.pairs = []
        i = 0
        n = len(lines)
        while i < n - 1:
            code = lines[i].strip()
            val = lines[i + 1]
            try:
                code = int(code)
                self.pairs.append((code, val))
            except ValueError:
                # If code is not an integer, skip/synchronize
                pass
            i += 2
        return self.pairs

    def get_entities_section(self):
        """Extract the ENTITIES section from parsed pairs."""
        if not self.pairs:
            self.parse()

        start = None
        end = None
        for idx, (c, v) in enumerate(self.pairs):
            if c == 2 and v == 'ENTITIES':
                start = idx
            if c == 0 and v == 'ENDSEC' and start is not None and end is None and idx > start:
                end = idx
                break
        if start is not None and end is not None:
            return self.pairs[start:end]
        return []

    def split_entities(self, section_pairs=None):
        """Split a list of pairs into individual entities, starting with group code 0."""
        if section_pairs is None:
            section_pairs = self.get_entities_section()

        self.entities = []
        cur = None
        for c, v in section_pairs:
            if c == 0:
                if cur is not None:
                    self.entities.append(cur)
                cur = [(c, v)]
            else:
                if cur is not None:
                    cur.append((c, v))
        if cur is not None:
            self.entities.append(cur)
        return self.entities
