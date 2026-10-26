import io
import json
import unittest
from zipfile import ZipFile
from parser import parse_upload, terms_from_query, text_matches

class ParserTests(unittest.TestCase):
    def test_meta_json(self):
        source = {'likes_media_likes': [{'title':'someone', 'string_list_data':[{'href':'https://www.instagram.com/reel/AbC_123/?igsh=123','timestamp':123}]}]}
        result = parse_upload('liked_posts.json', json.dumps(source).encode())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'reel')
        self.assertEqual(result[0]['url'], 'https://www.instagram.com/reel/AbC_123/')
    def test_zip(self):
        buf = io.BytesIO()
        with ZipFile(buf,'w') as z:
            z.writestr('your_instagram_activity/likes/liked_posts.json', json.dumps([{'href':'https://www.instagram.com/p/Foobar/'}]))
        self.assertEqual(len(parse_upload('export.zip',buf.getvalue())),1)
    def test_reject_bad_links(self):
        self.assertEqual(parse_upload('liked.csv',b'url\nhttps://evil.test/p/xyz/\n'),[])
    def test_hashtag(self):
        row={'caption':'Amazing biryani dinner','hashtags':'#food'}
        self.assertTrue(text_matches(row,terms_from_query('#biryani, #travel')))
        self.assertFalse(text_matches(row,terms_from_query('#biryani, #travel'),True))

if __name__=='__main__': unittest.main()
