# mmc_generator.py (is_valid_xml_structure 함수 추가 최종 버전)

import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
import pandas as pd

def strip_dot_zero(val) -> str:
    if val is None:
        return val
    try:
        num = float(val)
        num = round(num, 2)
        if num.is_integer():
            return "{:.1f}".format(num)
        else:
            return "{:.2f}".format(num).rstrip('0').rstrip('.')
    except (ValueError, TypeError):
        return str(val)

def add_prefix_if_needed(val, prefix: str) -> str:
    if val and not str(val).startswith(prefix):
        return prefix + str(val)
    return val

def is_valid_xml_structure(xml_string: str) -> bool:
    """
    XML 문자열이 유효한 구조인지 확인
    """
    try:
        ET.fromstring(xml_string)
        return True
    except ET.ParseError:
        return False

def csv_rows_to_xml_string(rows: list[dict]) -> str:
    root_info = next(r for r in rows if r.get('Type') == 'Root')
    tracks = [r for r in rows if r.get('Type') in ('Audio', 'Video', 'Subtitle')]

    NS = {
        'manifest': 'http://www.movielabs.com/schema/manifest/v1.5/manifest',
        'md':       'http://www.movielabs.com/schema/md/v2.4/md',
        'xsi':      'http://www.w3.org/2001/XMLSchema-instance'
    }

    manifest = ET.Element('manifest:MediaManifest', {
        'xmlns:manifest':     NS['manifest'],
        'xmlns:md':           NS['md'],
        'xmlns:xsi':          NS['xsi'],
        'xsi:schemaLocation': 'http://www.movielabs.com/schema/manifest/v1.5/manifest manifest-v1.5.xsd'
    })

    compatibility = ET.SubElement(manifest, 'manifest:Compatibility')
    ET.SubElement(compatibility, 'manifest:SpecVersion').text = '1.5'
    ET.SubElement(compatibility, 'manifest:Profile').text = 'MMC-1'

    inventory = ET.SubElement(manifest, 'manifest:Inventory')
    for track in tracks:
        track_type = track.get('Type')
        if track_type == 'Audio':
            audio = ET.SubElement(inventory, 'manifest:Audio', AudioTrackID=add_prefix_if_needed(track['Track ID'], 'md:audtrackid:org:'))
            ET.SubElement(audio, 'md:Type').text = track.get('Type/Format', '')
            ET.SubElement(audio, 'md:Language').text = track.get('Language', '')
            container_ref = ET.SubElement(audio, 'manifest:ContainerReference')
            ET.SubElement(container_ref, 'manifest:ContainerLocation').text = track.get('Location', '')

        elif track_type == 'Video':
            video = ET.SubElement(inventory, 'manifest:Video', VideoTrackID=add_prefix_if_needed(track['Track ID'], 'md:vidtrackid:org:'))
            ET.SubElement(video, 'md:Type').text = track.get('Type/Format', '')
            ET.SubElement(video, 'md:Language').text = track.get('Language', '')
            picture = ET.SubElement(video, 'md:Picture')
            ET.SubElement(picture, 'md:WidthPixels').text = strip_dot_zero(track.get('Width', ''))
            ET.SubElement(picture, 'md:HeightPixels').text = strip_dot_zero(track.get('Height', ''))
            ET.SubElement(picture, 'md:Progressive').text = 'true'
            container_ref = ET.SubElement(video, 'manifest:ContainerReference')
            ET.SubElement(container_ref, 'manifest:ContainerLocation').text = track.get('Location', '')

        elif track_type == 'Subtitle':
            subtitle = ET.SubElement(inventory, 'manifest:Subtitle', SubtitleTrackID=add_prefix_if_needed(track['Track ID'], 'md:subtrackid:org:'))
            ET.SubElement(subtitle, 'md:Format').text = track.get('Format', '')
            ET.SubElement(subtitle, 'md:Type').text = track.get('Type/Format', '')
            ET.SubElement(subtitle, 'md:Language').text = track.get('Language', '')
            encoding = ET.SubElement(subtitle, 'md:Encoding')
            frame_rate_value = strip_dot_zero(track.get('FrameRate'))
            if frame_rate_value:
                frame_rate = ET.SubElement(encoding, 'md:FrameRate', timecode="Drop")
                frame_rate.text = frame_rate_value
            container_ref = ET.SubElement(subtitle, 'manifest:ContainerReference')
            ET.SubElement(container_ref, 'manifest:ContainerLocation').text = track.get('Location', '')

    presentations = ET.SubElement(manifest, 'manifest:Presentations')
    presentation = ET.SubElement(presentations, 'manifest:Presentation', PresentationID=add_prefix_if_needed(root_info['PresentationID'], 'md:presentationid:org:'))
    track_metadata = ET.SubElement(presentation, 'manifest:TrackMetadata')
    ET.SubElement(track_metadata, 'manifest:TrackSelectionNumber').text = '0'

    video_ref = ET.SubElement(track_metadata, 'manifest:VideoTrackReference')
    ET.SubElement(video_ref, 'manifest:VideoTrackID').text = next(add_prefix_if_needed(t['Track ID'], 'md:vidtrackid:org:') for t in tracks if t.get('Type') == 'Video')

    audio_ref = ET.SubElement(track_metadata, 'manifest:AudioTrackReference')
    ET.SubElement(audio_ref, 'manifest:AudioTrackID').text = next(add_prefix_if_needed(t['Track ID'], 'md:audtrackid:org:') for t in tracks if t.get('Type') == 'Audio')

    for subtitle_track in [t for t in tracks if t.get('Type') == 'Subtitle']:
        subtitle_ref = ET.SubElement(track_metadata, 'manifest:SubtitleTrackReference')
        ET.SubElement(subtitle_ref, 'manifest:SubtitleTrackID').text = add_prefix_if_needed(subtitle_track['Track ID'], 'md:subtrackid:org:')

    experiences = ET.SubElement(manifest, 'manifest:Experiences')
    experience = ET.SubElement(experiences, 'manifest:Experience',
                               ExperienceID=add_prefix_if_needed(root_info['ExperienceID'], 'md:experienceid:org:'),
                               version="1.0")
    ET.SubElement(experience, 'manifest:ContentID').text = add_prefix_if_needed(root_info['ContentID'], 'md:cid:org:')
    audiovisual = ET.SubElement(experience, 'manifest:Audiovisual', ContentID=add_prefix_if_needed(root_info['ContentID'], 'md:cid:org:'))
    ET.SubElement(audiovisual, 'manifest:Type').text = root_info['Experience Type']
    ET.SubElement(audiovisual, 'manifest:SubType').text = root_info['Experience Sub Type']
    ET.SubElement(audiovisual, 'manifest:PresentationID').text = add_prefix_if_needed(root_info['PresentationID'], 'md:presentationid:org:')

    experiences.append(ET.Comment('  Child Experiences (international)  '))

    alid_maps = ET.SubElement(manifest, 'manifest:ALIDExperienceMaps')
    alid_map = ET.SubElement(alid_maps, 'manifest:ALIDExperienceMap')
    alid_value = add_prefix_if_needed(root_info['ExperienceID'], 'md:experienceid:org:').replace('md:experienceid:org:', 'md:ALID:org:').replace(':experience', '')
    ET.SubElement(alid_map, 'manifest:ALID').text = alid_value
    ET.SubElement(alid_map, 'manifest:ExperienceID').text = add_prefix_if_needed(root_info['ExperienceID'], 'md:experienceid:org:')

    rough_xml = ET.tostring(manifest, 'utf-8')
    parsed_xml = minidom.parseString(rough_xml).toprettyxml(indent="    ")
    
    # UTF-8 선언 추가
    xml_with_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n' + '\n'.join(parsed_xml.split('\n')[1:])

    return xml_with_declaration

def generate_mmc_xml_from_dataframe(df: pd.DataFrame) -> str:
    rows = df.to_dict(orient='records')
    return csv_rows_to_xml_string(rows)
