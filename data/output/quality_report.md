# Ramayana RAG Extraction Quality Report

## Processing Summary

- Total pages in PDF: 248
- Extracted page records: 248
- Cleaned page records: 248
- Text-based pages: 247
- Mixed pages: 0
- Scanned pages: 0
- Garbled/weak pages: 1
- OCR recommended pages: 1
- Translated records: 247
- Final chunks: 181

## Chunk Statistics

- Average chunk word count: 354.3
- Minimum chunk word count: 105
- Maximum chunk word count: 700

## Validation Summary

- Validation errors: 0
- Validation warnings: 0
- Validation status: PASS

## DeepSeek Configuration

- Model: deepseek-chat
- Review pass enabled: True
- Glossary entries: 34

## Sample Chunks

### front_matter_chapter_000_chunk_001

- Kanda: Front Matter
- Chapter: 0
- Pages: 2 - 3
- Keywords: Sri Ramayana, Question and Answer, Valmiki, Gita Press, Govindaraja commentary, 535 Sargas, 39 chapters, clue words, Ramayana, quiz, understanding, summary, answers, students

About Sri Ramayana - Question and Answer The author of the original Ramayana, Maharshi Valmiki, through his composition, at whatever auspicious time he began the Sri Mad Ramayana, by his effort, he has made the story of Rama live in every nerve of all humanity in the world today. The Ramayana always remains new. In all the poems written by many eminent poets over several thousand years, the shades of the Ramayana are visible. From great poets like Kalidasa up to the present day, many learned individuals who have read the Ramayana have either translated it or, based on the Ramayana, have produced many poems to the best of their ability. That is, the Ramayana has reached the masses in many...

### bala_kanda_chapter_002_chunk_002

- Kanda: Bala Kanda
- Chapter: 2
- Pages: 4 - 4
- Keywords: table of contents, Bala Kanda, Ayodhya Kanda, chapters

Table of Contents S.No. Subject Page No. 1. Bala Kanda - First Chapter 2. Bala Kanda - Second Chapter 3. Bala Kanda - Third Chapter 4. Bala Kanda - Fourth Chapter 5. Bala Kanda - Fifth Chapter 6. Bala Kanda - Sixth Chapter 7. Bala Kanda - Seventh Chapter 8. Bala Kanda - Eighth Chapter 9. Bala Kanda - Ninth Chapter 10. Bala Kanda - Tenth Chapter 11. Bala Kanda - Eleventh Chapter 12. Bala Kanda - Twelfth Chapter 13. Bala Kanda - Thirteenth Chapter 14. Ayodhya Kanda - Fourteenth Chapter 15. Ayodhya Kanda - Fifteenth Chapter 16. Ayodhya Kanda - Sixteenth Chapter 17. Ayodhya Kanda - Seventeenth Chapter 18. Ayodhya Kanda - Eighteenth Chapter 19. Ayodhya Kanda - Nineteenth Chapter 20. Ayodhya Ka...

### bala_kanda_chapter_026_chunk_003

- Kanda: Bala Kanda
- Chapter: 26
- Pages: 5 - 5
- Keywords: Ayodhya Kanda, Aranya Kanda, Kishkindha Kanda, chapter list

25. Ayodhya Kanda - Twenty-fifth Chapter 26. Ayodhya Kanda - Twenty-sixth Chapter 27. Ayodhya Kanda - Twenty-seventh Chapter 28. Ayodhya Kanda - Twenty-eighth Chapter 29. Ayodhya Kanda - Twenty-ninth Chapter 30. Ayodhya Kanda - Thirtieth Chapter 31. Ayodhya Kanda - Thirty-first Chapter 32. Ayodhya Kanda - Thirty-second Chapter 33. Aranya Kanda - Thirty-third Chapter 34. Aranya Kanda - Thirty-fourth Chapter 35. Aranya Kanda - Thirty-fifth Chapter 36. Aranya Kanda - Thirty-sixth Chapter 37. Aranya Kanda - Thirty-seventh Chapter 38. Aranya Kanda - Thirty-eighth Chapter 39. Aranya Kanda - Thirty-ninth Chapter 40. Aranya Kanda - Fortieth Chapter 41. Aranya Kanda - Forty-first Chapter 42. Arany...

## Known Limitations

- Metadata detection is semi-automatic and should be reviewed in `data/extracted/metadata_map.json`.
- OCR quality depends on local Tesseract installation and Telugu traineddata.
- Translation and review are intentionally DeepSeek-gated; no final Ramayana translation is fabricated without the API call.
- Ambiguous OCR text should remain marked in notes instead of being guessed.

## Security

- `.env` is ignored and must never be committed.
- API keys are read from environment variables only.
- Logs are ignored and should be reviewed before sharing if they are manually included.
