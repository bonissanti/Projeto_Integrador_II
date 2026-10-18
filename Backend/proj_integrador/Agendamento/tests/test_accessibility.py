from collections import Counter
from html.parser import HTMLParser

from django.test import TestCase


class PageAccessibilityParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = Counter()
        self.label_targets = []
        self.headings = []
        self.heading_ids = []
        self.main_ids = []
        self.document_language = None
        self.navigation_labels = []
        self.fieldset_legends = []
        self.nonsemantic_click_handlers = []
        self.image_alts = []
        self.button_names = []
        self.form_controls = []
        self.aria_references = []
        self.step_panels = []
        self.alert_regions = []
        self.status_regions = []
        self._fieldset_legend_counts = []
        self._button_text = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get('id')
        if element_id:
            self.ids[element_id] += 1
        if tag == 'html':
            self.document_language = attributes.get('lang')
        if tag == 'label' and attributes.get('for'):
            self.label_targets.append(attributes['for'])
        if tag in {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            self.headings.append(tag)
            if element_id:
                self.heading_ids.append(element_id)
        if tag == 'main' and element_id:
            self.main_ids.append(element_id)
        if tag == 'nav':
            self.navigation_labels.append(attributes.get('aria-label', ''))
        for attribute in ('aria-labelledby', 'aria-describedby', 'aria-controls'):
            self.aria_references.extend(attributes.get(attribute, '').split())
        if tag in {'input', 'select', 'textarea'}:
            self.form_controls.append((
                element_id,
                attributes.get('aria-label'),
                attributes.get('aria-labelledby'),
            ))
        if tag == 'section' and 'step-panel' in attributes.get('class', '').split():
            self.step_panels.append((
                element_id,
                attributes.get('aria-labelledby'),
                'hidden' in attributes,
            ))
        if attributes.get('role') == 'alert':
            self.alert_regions.append(attributes.get('aria-atomic'))
        if attributes.get('role') == 'status':
            self.status_regions.append((
                attributes.get('aria-live'),
                attributes.get('aria-atomic'),
            ))
        if tag == 'fieldset':
            self._fieldset_legend_counts.append(0)
        elif tag == 'legend' and self._fieldset_legend_counts:
            self._fieldset_legend_counts[-1] += 1
        if tag == 'img':
            self.image_alts.append(attributes.get('alt'))
        if 'onclick' in attributes and tag not in {'button', 'a', 'input', 'select'}:
            self.nonsemantic_click_handlers.append(tag)
        if tag == 'button':
            self._button_text.append([attributes.get('aria-label', '')])

    def handle_endtag(self, tag):
        if tag == 'fieldset' and self._fieldset_legend_counts:
            self.fieldset_legends.append(self._fieldset_legend_counts.pop())
        if tag == 'button' and self._button_text:
            self.button_names.append(' '.join(self._button_text.pop()).strip())

    def handle_data(self, data):
        if self._button_text:
            self._button_text[-1].append(data.strip())


class AccessibilityPageTests(TestCase):
    def _get_page(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        parser = PageAccessibilityParser()
        parser.feed(html)
        parser.close()
        return html, parser

    def test_public_pages_include_skip_link_and_main_landmark(self):
        for url in ('/', '/agendar/'):
            with self.subTest(url=url):
                html, parser = self._get_page(url)
                self.assertIn('href="#main-content"', html)
                self.assertEqual(parser.main_ids, ['main-content'])
                self.assertEqual(parser.document_language, 'pt-BR')
                self.assertTrue(all(count == 1 for count in parser.ids.values()))
                self.assertTrue(all(reference in parser.ids for reference in parser.aria_references))

    def test_home_page_has_one_main_heading_and_named_images(self):
        _, parser = self._get_page('/')

        self.assertEqual(parser.headings.count('h1'), 1)
        self.assertTrue(parser.image_alts)
        self.assertTrue(all(alt and alt.strip() for alt in parser.image_alts))

    def test_booking_steps_have_screen_reader_names_and_hide_inactive_panels(self):
        _, parser = self._get_page('/agendar/')

        self.assertEqual(len(parser.step_panels), 6)
        self.assertTrue(all(panel_id and heading_id in parser.heading_ids
                            for panel_id, heading_id, _ in parser.step_panels))
        self.assertEqual(
            [panel_id for panel_id, _, hidden in parser.step_panels if not hidden],
            ['step-1a'],
        )
        self.assertTrue(all(
            control_id and (
                control_id in parser.label_targets or aria_label or labelledby
            )
            for control_id, aria_label, labelledby in parser.form_controls
        ))

    def test_booking_controls_have_labels_and_semantic_groups(self):
        html, parser = self._get_page('/agendar/')
        control_ids = {
            'email-lookup',
            'novo-nome',
            'novo-telefone',
            'servico-select',
            'loc-salao',
            'loc-domicilio',
            'endereco',
        }

        self.assertTrue(control_ids.issubset(set(parser.label_targets)))
        self.assertEqual(parser.fieldset_legends, [1, 1])
        self.assertEqual(parser.nonsemantic_click_handlers, [])
        self.assertTrue(all(parser.button_names))
        self.assertEqual(parser.navigation_labels, ['Navegação principal'])
        self.assertIn(('polite', 'true'), parser.status_regions)

    def test_step_errors_and_contrast_toggle_are_exposed_accessibly(self):
        html, parser = self._get_page('/agendar/')

        for alert_id in ('alert-1a', 'alert-1b', 'alert-1c', 'alert-2', 'alert-3'):
            self.assertIn(f'id="{alert_id}" role="alert"', html)
        self.assertEqual(parser.alert_regions, ['true'] * 5)

        self.assertIn('id="a11y-toggle-btn"', html)
        self.assertIn('aria-pressed="false"', html)
        self.assertIn('aria-label="Ativar alto contraste"', html)
