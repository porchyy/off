# PostureAI blank enclosure

This is a deliberately blank two-piece enclosure for later drilling or cutting.

| Dimension | Size |
| --- | ---: |
| Outside width | 160 mm |
| Outside height | 240 mm |
| Outside depth | 80 mm |
| Wall thickness | 3 mm |
| Nominal usable internal space | 154 × 234 × 74 mm |
| Camera-centre reference height | 190 mm from the base |

`postureai-empty-enclosure.blend` contains two separate printable objects:

- `Front shell — blank exterior`: closed front and sides, open at the rear.
- `Rear cover — blank exterior`: a solid rear panel with a 6 mm insertion lip.

No holes, mounting posts, vents, or component openings are included. Check the
fit of the Pi 5, LCD, camera ribbon, and wiring before drilling or cutting.
The two STL files are exported in millimetres for a slicer.

To regenerate the files in Blender:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe' --background --python .\build_enclosure.py
```
