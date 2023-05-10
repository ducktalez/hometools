import yaml
from pathlib import Path


def yaml_dump(p: Path, data):
    with p.open('w') as f:
        yaml.dump(data, f)


if __name__ == '__main__':
    p = Path.cwd() / 'wa_data/mp3files_lut.yaml'
    try:
        with p.open('r') as file:
            yaml_content = yaml.load(file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        raise FileNotFoundError

    delkeys = ['DISPOSITION',
               'codec_name', 'avg_frame_rate', 'bits_per_raw_sample', 'bits_per_sample', 'channel_layout', 'channels',
               'chroma_location', 'closed_captions', 'codec_long_name', 'codec_tag', 'codec_tag_string', 'codec_type',
               'coded_height', 'coded_width', 'color_primaries', 'color_range', 'color_space', 'color_transfer',
               'display_aspect_ratio', 'duration_ts', 'field_order', 'filename', 'film_grain', 'format_long_name',
               'format_name', 'has_b_frames', 'height', 'id', 'index', 'initial_padding', 'level', 'max_bit_rate',
               'nb_frames', 'nb_programs', 'nb_read_frames', 'nb_read_packets', 'nb_streams', 'pix_fmt', 'probe_score',
               'profile', 'r_frame_rate', 'refs', 'sample_aspect_ratio', 'sample_fmt', 'start_pts', 'time_base', 'width']
    for k, v in yaml_content.items():
        for dt in delkeys:
            try:
                v.pop(dt)
            except KeyError as ex:
                pass

    yaml_dump(p, yaml_content)


