import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import '../../core/config.dart';
import '../../providers/appraisal_provider.dart';
import '../../widgets/custom_card.dart';
import '../../widgets/status_badge.dart';

class MyAppraisalsScreen extends StatefulWidget {
  const MyAppraisalsScreen({super.key});

  @override
  State<MyAppraisalsScreen> createState() => _MyAppraisalsScreenState();
}

class _MyAppraisalsScreenState extends State<MyAppraisalsScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      Provider.of<AppraisalProvider>(context, listen: false).fetchMyAppraisals();
    });
  }

  @override
  Widget build(BuildContext context) {
    final appraisalProvider = Provider.of<AppraisalProvider>(context);

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Text('My Appraisals'),
      ),
      body: appraisalProvider.isLoading
          ? const Center(child: SpinKitFadingCube(color: AppConfig.primaryColor, size: 40))
          : appraisalProvider.myAppraisals.isEmpty
              ? Center(
                  child: Text(
                    'No appraisals found.',
                    style: TextStyle(color: context.textSecondary),
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: appraisalProvider.myAppraisals.length,
                  itemBuilder: (context, index) {
                    final item = appraisalProvider.myAppraisals[index];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: CustomCard(
                        onTap: () {
                          Navigator.pushNamed(
                            context,
                            '/appraisal_detail',
                            arguments: item.id,
                          );
                        },
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Expanded(
                                  child: Text(
                                    item.cycleName,
                                    style: TextStyle(
                                      color: context.textPrimary,
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                StatusBadge(status: item.status, displayLabel: item.statusDisplay),
                              ],
                            ),
                            const SizedBox(height: 12),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(
                                  'Self Score: ${item.overallSelfScore ?? 'N/A'}',
                                  style: TextStyle(color: context.textSecondary, fontSize: 13),
                                ),
                                Text(
                                  'Supervisor Score: ${item.overallSupervisorScore ?? 'N/A'}',
                                  style: const TextStyle(color: AppConfig.secondaryColor, fontSize: 13, fontWeight: FontWeight.bold),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
