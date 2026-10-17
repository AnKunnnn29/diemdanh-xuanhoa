"""Register sprites using neck, head width and belt landmarks; never edit PNG pixels."""
from pathlib import Path
from PIL import Image
import numpy as np
import json

def components(mask):
    todo = set(map(tuple, np.argwhere(mask)))
    result = []
    while todo:
        queue = [todo.pop()]
        points = []
        while queue:
            y, x = queue.pop()
            points.append((y, x))
            for point in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if point in todo:
                    todo.remove(point)
                    queue.append(point)
        ys, xs = np.array(points).T
        result.append({'count': len(points), 'x': float(xs.mean()), 'y': float(ys.mean()),
                       'box': [int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)]})
    return result

result = {}
for kind, filename, rows in [
    ('cover', 'glv-cover-sequence-v5.png', 3),
    ('expression', 'glv-expression-sequence-v5.png', 4),
]:
    with Image.open(Path('design/mascot') / filename) as image:
        pixels = np.array(image)
        width, height = image.size
    alpha = pixels[:, :, 3] > 160
    columns = [round(width * i / 4) for i in range(5)]
    row_cuts = []
    for col in range(4):
        counts = alpha[:, columns[col]:columns[col + 1]].sum(axis=1)
        cuts = [0]
        for row in range(1, rows):
            center = round(height * row / rows)
            lower, upper = center - 65, center + 65
            candidates = np.flatnonzero(counts[lower:upper] == counts[lower:upper].min()) + lower
            cuts.append(int(candidates[np.argmin(abs(candidates - center))]))
        row_cuts.append(cuts + [height])
    frames = []
    for row in range(rows):
        for col in range(4):
            x0, x1 = columns[col:col + 2]
            y0, y1 = row_cuts[col][row:row + 2]
            region = alpha[y0:y1, x0:x1]
            active_rows = np.flatnonzero(region.sum(axis=1) > 8)
            active_columns = np.flatnonzero(region.sum(axis=0) > 8)
            top, bottom = int(active_rows[0]), int(active_rows[-1]) + 1
            left, right = int(active_columns[0]), int(active_columns[-1]) + 1
            center = float(np.argwhere(region[max(top, bottom - 14):bottom])[:, 1].mean())
            r, g, b, a = pixels[y0:y1, x0:x1].astype(float).transpose(2, 0, 1)
            yy, xx = np.indices(a.shape)
            grey = ((np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b]) < 24)
                    & (r > 110) & (a > 180) & (yy > top+(bottom-top)*.88)
                    & (abs(xx-center) < (right-left)*.14))
            candidates = [component for component in components(grey) if component['count'] > 15]
            if not candidates:
                raise ValueError(f'Cannot locate belt buckle: {kind}{len(frames)}')
            belt = max(candidates, key=lambda component: component['y'])
            skin = ((r > 210) & (g > 115) & (g < 210) & (b > 80) & (b < 190)
                    & (r-g > 25) & (a > 180) & (abs(xx-center) < (right-left)*.03)
                    & (yy > top+(bottom-top)*.5) & (yy < top+(bottom-top)*.8))
            neck_rows = np.flatnonzero(skin.sum(axis=1) > 4)
            if not len(neck_rows):
                raise ValueError(f'Cannot locate neck: {kind}{len(frames)}')
            neck = int(neck_rows[-1]) + 1
            head_columns = np.flatnonzero(region[top:neck].sum(axis=0) > 8)
            head_width = int(head_columns[-1]-head_columns[0]+1)
            belt_row = round(belt['y'])
            waist_columns = np.flatnonzero(region[belt_row-2:belt_row+3].sum(axis=0) > 1)
            waist_width = int(waist_columns[-1]-waist_columns[0]+1)
            frames.append({'name': f'{kind}{len(frames)}', 'rect': [x0,y0,x1-x0,y1-y0],
                           'clip': [x0+left,y0+top,right-left,bottom-top],
                           'landmarks': {'top': top, 'neck': neck, 'belt': belt['y'],
                                         'bottom': bottom, 'beltX': belt['x'], 'headWidth': head_width,
                                         'waistWidth': waist_width}})
    result[kind] = {'file': filename, 'width': width, 'height': height, 'frames': frames}

# Keep the approved neutral pose as the reference. Other poses must share its
# head dimensions, neck-to-belt length and buckle position, rather than merely
# fitting their full bounding boxes to the same overall height.
reference = result['expression']['frames'][2]['landmarks']
reference_scale = 484 / (reference['bottom']-reference['top'])
targets = [16, 16+(reference['neck']-reference['top'])*reference_scale,
           16+(reference['belt']-reference['top'])*reference_scale, 500]
target_head_width = reference['headWidth']*reference_scale
target_waist_width = reference['waistWidth']*reference_scale
for sheet in result.values():
    for frame in sheet['frames']:
        mark = frame['landmarks']
        source = [mark['top'],mark['neck'],mark['belt'],mark['bottom']]
        head_scale_x = target_head_width/mark['headWidth']
        body_scale_x = target_waist_width/mark['waistWidth']
        x0,y0,_,_ = frame['rect']
        cx,cy,cw,ch = frame['clip']
        bands = []
        # Blend horizontal correction across the neck, so arms, shirt outlines
        # and backpack do not acquire a hard seam where head and torso meet.
        blend_top,blend_bottom = targets[1]-24,targets[1]+24
        target_cuts = sorted(set(targets+[blend_top+i*4 for i in range(13)]))
        def source_y(target):
            index = min(2,max(0,int(np.searchsorted(targets,target,side='right'))-1))
            return source[index]+(target-targets[index])*(source[index+1]-source[index])/(targets[index+1]-targets[index])
        for target_start,target_end in zip(target_cuts,target_cuts[1:]):
            start,end = source_y(target_start),source_y(target_end)
            sy = (target_end-target_start)/(end-start)
            t = max(0,min(1,((target_start+target_end)/2-blend_top)/(blend_bottom-blend_top)))
            scale_x = head_scale_x+(body_scale_x-head_scale_x)*(t*t*(3-2*t))
            # Half-pixel overlap removes antialias cracks at the strip boundary.
            clip_top = max(cy,y0+start-.5)
            clip_bottom = min(cy+ch,y0+end+.5)
            bands.append({'clip': [cx,round(clip_top,4),cw,round(clip_bottom-clip_top,4)],
                          'scaleX': round(scale_x,7), 'scaleY': round(sy,7),
                          'x': round(240-mark['beltX']*scale_x,5),
                          'y': round(target_start-start*sy,5)})
        frame['bands'] = bands
result['registration'] = {'reference': 'expression2', 'headWidth': target_head_width,
                          'waistWidth': target_waist_width,
                          'top': targets[0], 'neck': targets[1], 'belt': targets[2],
                          'bottom': targets[3], 'beltX': 240}
Path('design/mascot/glv-sequences-v5.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result['registration']))
