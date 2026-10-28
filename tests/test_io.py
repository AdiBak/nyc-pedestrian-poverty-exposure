from nycped import io as nio
from nycped.config import Settings


def test_manifest_marks_existing_files_as_recorded_not_retrieved(tmp_path):
    s = Settings(data_dir=tmp_path)
    for name in nio.SOURCES:
        (tmp_path / name).write_bytes(b'example ' + name.encode())
    manifest = nio.fetch_all(s)
    assert set(manifest.entries) == set(nio.SOURCES)
    for name, entry in manifest.entries.items():
        assert 'recorded_utc' in entry and 'retrieved_utc' not in entry
        assert entry['sha256'] == nio.sha256_file(tmp_path / name)
        assert entry['bytes'] == (tmp_path / name).stat().st_size
        assert 'file_modified_utc' in entry


def test_second_fetch_keeps_the_original_entries(tmp_path):
    s = Settings(data_dir=tmp_path)
    for name in nio.SOURCES:
        (tmp_path / name).write_bytes(b'x')
    first = nio.fetch_all(s).entries
    second = nio.fetch_all(s).entries
    assert first == second


def test_manifest_round_trips_through_disk(tmp_path):
    m = nio.Manifest(tmp_path / 'MANIFEST.json')
    m.record('a.csv', 'https://example.org/a.csv', {'bytes': 3, 'sha256': 'abc'})
    again = nio.Manifest(tmp_path / 'MANIFEST.json')
    assert again.entries['a.csv']['sha256'] == 'abc'
    assert 'retrieved_utc' in again.entries['a.csv']
