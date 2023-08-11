"""
Report Library.

This library is part of ONE ITest framework.

@author:  jgonzalezsosa@one.com
@version: 1.0.0

@change:  jgonzalezsosa - 1.0.0 - Integration test report hith hyperlinks
"""

import datetime
import os
import re
from collections import defaultdict
from jinja2 import Template
from lxml import etree

class ITestReport(object):
    """
    Integration Test Report

    This class manages the Integration Test Report, it creates all the required
    methods to create test cases and reporting on HTML.
    """
    def __init__(self, swc='', swc_ver='', revision='', tester='', hw_version=''):
        self.data_dic = {
            'swc_name': swc,
            'version': swc_ver,
            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            'revision': revision,
            'author': tester,
            'hw_version': hw_version,
            'summary': defaultdict(int),
            'summary_test_cases': [],
            'test_cases': []
        }

    def add_test_case(self, name='', desc='', req='', ini_cond='', action='', eva_criteria=''):
        """
        Creating test case. This method populates the required information in the data dictionary.
        """
        test_case = {
            'NAME': name,
            'DESCRIPTION': desc,
            'REQUIREMENT': req,
            'INITIAL_CONDITIONS': ini_cond,
            'ACTIONS': action,
            'EVAL_CRITERIA': eva_criteria,
            'TEST_STEP': []
        }
        self.data_dic['test_cases'].append(test_case)

    def add_test_step( self, name = '', result = 'OK', comments = '' ):
        """ Add test step to a test case. """
        ind = len( self.data_dic['test_cases'] )
        test_case = self.data_dic['test_cases'][0 if ind == 0 else ( ind - 1 )]

        if result in ['OK', 'NOK', 'NT']:
            test_case.setdefault( 'TEST_STEP', [] ).append( {
                'NAME': name,
                'RESULT': result,
                'COMMENTS': comments
            } )
        else:
            exit( f"Invalid test result ({result}) passed in the this test case -- {name} --.\nUse OK/NOK/NT for the result." )

    def add_manual_test_step(self, name='', result='OK', comments=''):
        cmd = ""
        print(f'Manual test case: {name}')
        while cmd.upper() not in ['OK', 'NOK', 'NT']:
            cmd = input('Enter the result [OK/NOK]/NT: ')

        comments = input('Enter your comments: ')

        self.add_test_step(name, result, comments)

    def _build_summary(self):
        for test_case in self.data_dic['test_cases']:
            name = test_case['NAME']
            sub_total_ok = sum(1 for step in test_case['TEST_STEP'] if step['RESULT'] == 'OK')
            sub_total_nok = sum(1 for step in test_case['TEST_STEP'] if step['RESULT'] == 'NOK')
            sub_total_nt = sum(1 for step in test_case['TEST_STEP'] if step['RESULT'] not in ['OK', 'NOK'])

            self.data_dic['summary']['TOTAL_RUN_TEST'] += (sub_total_ok + sub_total_nok + sub_total_nt)
            self.data_dic['summary']['TOTAL_TEST_OK'] += sub_total_ok
            self.data_dic['summary']['TOTAL_TEST_KO'] += sub_total_nok
            self.data_dic['summary']['TOTAL_NOT_TESTED'] += sub_total_nt

            self.data_dic['summary_test_cases'].append({
                'NAME': name,
                'TEST_OK': sub_total_ok,
                'TEST_KO': sub_total_nok,
                'NOT_TESTED': sub_total_nt,
            })

    def gen_report(self, file_name='report.html'):
        """ Generate the HTML report combining XML and XSL files """

        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, 'template.xml')

        with open(template_path, 'r') as template_file:
            template_string = template_file.read()
            template = Template(template_string)

        self._build_summary()

        xml = template.render(**self.data_dic)
        xslt = etree.parse(os.path.join(current_dir, 'ITestStyle.xsl'))

        transform = etree.XSLT(xslt)
        new_dom = transform(etree.fromstring(xml))

        to_file = etree.tostring(new_dom, pretty_print=True, encoding='unicode')

        # Find lines containing 'href="#idm' or 'href="#idp'
        hyperlink_lines = [line for line in to_file.splitlines() if 'href="#idm' in line or 'href="#idp' in line]

        # Find lines containing '<a name="'
        anchor_lines = [line for line in to_file.splitlines() if '<a name="' in line]

        # Extract the hyperlink IDs from the lines
        hyperlink_ids = [re.findall(r'"([^"]*)"', line)[0][1:] for line in hyperlink_lines]

        # Replace the anchor lines with modified content
        for anchor_line, hyperlink_id in zip(anchor_lines, hyperlink_ids):
            modified_anchor_line = re.sub(r'".*"', f'"{hyperlink_id}"', anchor_line)
            to_file = to_file.replace(anchor_line, modified_anchor_line)

        # Write the modified to_file back to the file
        with open(file_name, "w") as fp:
            fp.write(to_file)

if __name__ == "__main__":
    ''' If the script is executed, it will run the report and validate the library '''
    
    test = ITestReport( 'Fault Injection Box', '1.0.0', '1', 'Jarold Gonzalez', 'Pcan-usb1' )

    # Test case creation.
    test.add_test_case('Test case example 2', 'Set different baudrate', 'Can bus and a receiver-Pcan ', 'NeoVI with vehicle spy is Connected to receive and pcan-view to python lib', 'Change baudrates', 'If Data-frame is received by vehicle-spy the result is OK')
    
    # Step for each test case.
    test.add_test_step('Set Baudrate value to 1000000 bps', 'OK', 'Frames received and transmitted')
    test.add_test_step('Set Baudrate value to 800000 bps', 'OK', 'Frames received and transmitted')
    test.add_test_step('Set Baudrate value to 500000 bps', 'OK', 'Frames received and transmitted')
    test.add_test_step('Set Baudrate value to 250000 bps', 'OK', 'Frames received and transmitted')
    test.add_test_step('Set Baudrate value to 100000 bps', 'OK', 'Frames received and transmitted')
    
    # Test case creation.
    test.add_test_case('Test case example 2','CAN-Bus shutdown','Can bus and a receiver-Pcan ','NeoVI with vehicle spy is Connected to receive and pcan-view to python lib','Shutdown the bus and try sending or receiving','If error occurs the result is OK')
    
    # Step for each test case.
    test.add_test_step('Shut down and send can frame','OK','Message NOT sent')
    test.add_test_step('Shut down and send_array - size 3','NT','Message NOT sent CanError - 3 times')
    test.add_test_step('Shut down and continOKuous receive frame','OK','A PCAN Channel has not been initialized yet or the initialization process has failed')
    test.add_test_step('Shut down and receive one frame','OK','A PCAN Channel has not been initialized yet or the initialization process has failed')
    test.add_manual_test_step('receive only one type of frame')

    # Compute the path to the report HTML
    current_dir = os.path.dirname(os.path.abspath(__file__))
    report_path = os.path.join(current_dir, 'unit_test.html')

    test.gen_report(report_path)
    print ("Report created")