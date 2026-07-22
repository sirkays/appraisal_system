import 'package:flutter_test/flutter_test.dart';
import 'package:appraisal_app/main.dart';

void main() {
  testWidgets('App load smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const AppraisalApp());
    expect(find.byType(AppraisalApp), findsOneWidget);
  });
}
