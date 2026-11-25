#!/usr/bin/env python3
"""Check documentation parity and the public ROS API against the source.

The checker is dependency-free and is intended to run from the repository root:

    python3 tools/check_docs.py

It verifies:
* every paired English document has a Russian counterpart;
* paired documents have the same heading structure, number of code fences,
  tables and Markdown links;
* both files of a pair link to each other through a language switcher;
* every topic, parameter and launch argument used in the source is documented;
* every interface message file and field is documented;
* every URDF link is listed in the ROS API document.
"""

import ast
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN = ROOT / 'docs' / 'en'
RU = ROOT / 'docs' / 'ru'

PAIRS = [
    (ROOT / 'README.md', ROOT / 'README.ru.md'),
    (EN / 'README.md', RU / 'README.md'),
    (EN / 'usage.md', RU / 'usage.md'),
    (EN / 'architecture.md', RU / 'architecture.md'),
    (EN / 'configuration.md', RU / 'configuration.md'),
    (EN / 'algorithms.md', RU / 'algorithms.md'),
    (EN / 'verification.md', RU / 'verification.md'),
    (EN / 'troubleshooting.md', RU / 'troubleshooting.md'),
    (EN / 'ros-api.md', RU / 'ros-api.md'),
    (EN / 'wsl-setup.md', RU / 'wsl-setup.md'),
]

DOCS_API = EN / 'ros-api.md'
DOCS_CONFIG = EN / 'configuration.md'
DOCS_VERIFICATION = EN / 'verification.md'


def fail(message):
    print('ERROR: ' + message)
    return 1


def heading_levels(text):
    return [len(match.group(1)) for match in re.finditer(r'^(#{1,6}) ', text, re.M)]


def count_table_lines(text):
    return sum(1 for line in text.splitlines() if line.startswith('|'))


def count_list_items(text):
    return len(re.findall(r'^\s*(?:[-*]|\d+\.)\s', text, re.M))


def count_links(text):
    return len(re.findall(r'\]\([^)]+\)', text))


def check_pairs():
    errors = 0
    for en_path, ru_path in PAIRS:
        if not en_path.exists():
            errors += fail('missing English document: %s' % en_path.relative_to(ROOT))
            continue
        if not ru_path.exists():
            errors += fail('missing Russian document: %s' % ru_path.relative_to(ROOT))
            continue

        en = en_path.read_text(encoding='utf-8')
        ru = ru_path.read_text(encoding='utf-8')

        if heading_levels(en) != heading_levels(ru):
            errors += fail('heading structure differs: %s / %s' % (
                en_path.relative_to(ROOT), ru_path.relative_to(ROOT)))
        if en.count('```') != ru.count('```') or en.count('```') % 2:
            errors += fail('code fences differ or are unbalanced: %s / %s' % (
                en_path.relative_to(ROOT), ru_path.relative_to(ROOT)))
        if count_table_lines(en) != count_table_lines(ru):
            errors += fail('table row count differs: %s / %s' % (
                en_path.relative_to(ROOT), ru_path.relative_to(ROOT)))
        if count_list_items(en) != count_list_items(ru):
            errors += fail('list item count differs: %s / %s' % (
                en_path.relative_to(ROOT), ru_path.relative_to(ROOT)))
        if count_links(en) != count_links(ru):
            errors += fail('link count differs: %s / %s' % (
                en_path.relative_to(ROOT), ru_path.relative_to(ROOT)))

        if en_path == ROOT / 'README.md':
            expected_en = 'README.ru.md'
            expected_ru = 'README.md'
        else:
            expected_en = '../ru/' + ru_path.name
            expected_ru = '../en/' + en_path.name

        if expected_en not in en:
            errors += fail('missing language switcher in %s' % en_path.relative_to(ROOT))
        if expected_ru not in ru:
            errors += fail('missing language switcher in %s' % ru_path.relative_to(ROOT))
    return errors


def string_constants(path):
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except SyntaxError as exc:
        raise RuntimeError('%s: %s' % (path, exc))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value


def collect_topics():
    topics = set()
    for path in sorted(ROOT.glob('src/*/**/*_node.py')):
        if 'test' in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, 'attr', None)
            if name in ('create_publisher', 'create_subscription'):
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    value = node.args[1].value
                    if isinstance(value, str) and value.startswith('/'):
                        topics.add(value)
            elif name == 'declare_parameter' and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    if first.value.endswith('_topic') and len(node.args) >= 2:
                        second = node.args[1]
                        if isinstance(second, ast.Constant) and isinstance(second.value, str):
                            if second.value.startswith('/'):
                                topics.add(second.value)
    for path in sorted(ROOT.glob('src/navigator_bringup/launch/*.py')):
        for value in string_constants(path):
            if value.startswith('/') and not value.startswith(('/opt/', '/cfg/', '/**')):
                topics.add(value)
    return topics


def collect_parameters():
    parameters = set()
    for path in sorted(ROOT.glob('src/*/**/*.py')):
        if 'test' in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if getattr(func, 'attr', None) == 'declare_parameter' and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    parameters.add(first.value)
    return parameters


def collect_launch_arguments():
    arguments = set()
    for path in sorted(ROOT.glob('src/navigator_bringup/launch/*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if getattr(node.func, 'id', '') != 'DeclareLaunchArgument' or not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                arguments.add(first.value)
    return arguments


def collect_message_fields():
    messages = {}
    for path in sorted(ROOT.glob('src/navigator_interfaces/msg/*.msg')):
        fields = []
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.split('#', 1)[0].strip()
            if not line or line.startswith('---'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                fields.append(parts[-1])
        messages[path.stem] = fields
    return messages


def collect_urdf_links():
    path = ROOT / 'src' / 'navigator_description' / 'urdf' / 'navigator_m.urdf'
    tree = ET.parse(path)
    return [element.get('name') for element in tree.getroot().findall('link')]


def require_in_document(what, values, document, pattern=None):
    errors = 0
    text = document.read_text(encoding='utf-8')
    for value in sorted(values):
        if pattern:
            found = re.search(pattern % re.escape(value), text)
        else:
            found = re.search(r'(?<![A-Za-z0-9_/])' + re.escape(value) +
                              r'(?![A-Za-z0-9_/])', text)
        if not found:
            errors += fail('%s is not documented: %s' % (what, value))
    return errors


def check_api():
    errors = 0
    api = DOCS_API.read_text(encoding='utf-8')
    config = DOCS_CONFIG.read_text(encoding='utf-8')
    verification = DOCS_VERIFICATION.read_text(encoding='utf-8')

    topics = collect_topics()
    errors += require_in_document('topic', topics, DOCS_API)

    parameters = collect_parameters()
    for name in sorted(parameters):
        if not re.search(r'(?<![A-Za-z0-9_])' + re.escape(name) +
                         r'(?![A-Za-z0-9_])', config):
            errors += fail('parameter is not documented: %s' % name)

    launch_arguments = collect_launch_arguments()
    for name in sorted(launch_arguments):
        if not re.search(r'(?<![A-Za-z0-9_])' + re.escape(name) +
                         r'(?![A-Za-z0-9_])', config):
            errors += fail('launch argument is not documented: %s' % name)

    for name, fields in sorted(collect_message_fields().items()):
        if name not in api:
            errors += fail('message type is not documented: %s' % name)
        for field in fields:
            if not re.search(r'(?<![A-Za-z0-9_])' + re.escape(field) +
                             r'(?![A-Za-z0-9_])', api):
                errors += fail('message field is not documented: %s.%s' % (name, field))

    for link in collect_urdf_links():
        if not re.search(r'(?<![A-Za-z0-9_])' + re.escape(link) +
                         r'(?![A-Za-z0-9_])', api):
            errors += fail('URDF link is not documented: %s' % link)

    if 'tools/check_docs.py' not in verification:
        errors += fail('tools/check_docs.py is not mentioned in verification.md')

    print('topics: %d, parameters: %d, launch arguments: %d, messages: %d' % (
        len(topics), len(parameters), len(launch_arguments),
        len(collect_message_fields())))
    return errors


def main():
    errors = check_pairs()
    errors += check_api()
    if errors:
        print('%d documentation problem(s) found.' % errors)
        return 1
    print('Documentation checks passed: %d language pairs.' % len(PAIRS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
