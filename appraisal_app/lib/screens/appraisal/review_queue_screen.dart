import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import '../../core/config.dart';
import '../../providers/appraisal_provider.dart';
import '../../providers/reviewer_provider.dart';
import '../../widgets/status_badge.dart';

class ReviewQueueScreen extends StatefulWidget {
  const ReviewQueueScreen({super.key});

  @override
  State<ReviewQueueScreen> createState() => _ReviewQueueScreenState();
}

class _ReviewQueueScreenState extends State<ReviewQueueScreen>
    with SingleTickerProviderStateMixin {
  final TextEditingController _searchController = TextEditingController();
  String _selectedFilter = 'ALL'; // ALL, PENDING, RETURNED
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final p = Provider.of<ReviewerProvider>(context, listen: false);
      p.fetchQueue();
      p.fetchHistory();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  // ── Filtering for the pending tab ───────────────────────────────────────────

  List<ReviewQueueItem> _filterQueue(List<ReviewQueueItem> queue) {
    final query = _searchController.text.trim().toLowerCase();
    return queue.where((item) {
      final appraisal = item.appraisal;

      final matchesSearch = query.isEmpty ||
          appraisal.staffName.toLowerCase().contains(query) ||
          appraisal.staffId.toLowerCase().contains(query) ||
          (appraisal.departmentName != null &&
              appraisal.departmentName!.toLowerCase().contains(query)) ||
          item.stepLabel.toLowerCase().contains(query);

      if (!matchesSearch) return false;

      if (_selectedFilter == 'RETURNED') {
        return appraisal.status == 'RETURNED_TO_REVIEWER';
      } else if (_selectedFilter == 'PENDING') {
        return appraisal.status != 'RETURNED_TO_REVIEWER';
      }

      return true;
    }).toList();
  }

  // ── Build ────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final reviewerProvider = Provider.of<ReviewerProvider>(context);
    final rawQueue = reviewerProvider.queue;
    final filteredQueue = _filterQueue(rawQueue);

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: Row(
          children: [
            const Text('Review Queue'),
            if (rawQueue.isNotEmpty) ...[
              const SizedBox(width: 8),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                decoration: BoxDecoration(
                  gradient: AppConfig.primaryGradient,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${rawQueue.length}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ],
        ),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppConfig.primaryColor,
          labelColor: AppConfig.primaryColor,
          unselectedLabelColor: context.textSecondary,
          labelStyle:
              const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
          tabs: const [
            Tab(text: 'Pending'),
            Tab(text: 'History'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildPendingTab(reviewerProvider, rawQueue, filteredQueue),
          _buildHistoryTab(reviewerProvider),
        ],
      ),
    );
  }

  // ── Tab 1: Pending Queue ─────────────────────────────────────────────────────

  Widget _buildPendingTab(ReviewerProvider reviewerProvider,
      List<ReviewQueueItem> rawQueue, List<ReviewQueueItem> filteredQueue) {
    if (reviewerProvider.isLoading) {
      return const Center(
          child: SpinKitFadingCube(color: AppConfig.primaryColor, size: 40));
    }

    return RefreshIndicator(
      onRefresh: () => reviewerProvider.fetchQueue(),
      child: Column(
        children: [
          // ── Search & Filter Bar ─────────────────────────────────
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: context.cardColor,
              border: Border(
                bottom: BorderSide(
                  color: context.textSecondary.withAlpha(25),
                ),
              ),
            ),
            child: Column(
              children: [
                TextField(
                  controller: _searchController,
                  onChanged: (_) => setState(() {}),
                  style: TextStyle(color: context.textPrimary, fontSize: 14),
                  decoration: InputDecoration(
                    hintText: 'Search staff, department, step...',
                    hintStyle:
                        TextStyle(color: context.textSecondary, fontSize: 14),
                    prefixIcon: const Icon(Icons.search,
                        color: AppConfig.primaryColor, size: 20),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear, size: 18),
                            onPressed: () {
                              _searchController.clear();
                              setState(() {});
                            },
                          )
                        : null,
                    filled: true,
                    fillColor: context.surfaceColor.withAlpha(80),
                    contentPadding:
                        const EdgeInsets.symmetric(vertical: 10),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(14),
                      borderSide: BorderSide.none,
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _buildFilterChip('ALL', 'All (${rawQueue.length})'),
                      const SizedBox(width: 8),
                      _buildFilterChip(
                        'PENDING',
                        'Awaiting (${rawQueue.where((i) => i.appraisal.status != 'RETURNED_TO_REVIEWER').length})',
                      ),
                      const SizedBox(width: 8),
                      _buildFilterChip(
                        'RETURNED',
                        'Returned (${rawQueue.where((i) => i.appraisal.status == 'RETURNED_TO_REVIEWER').length})',
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // ── Queue list ──────────────────────────────────────────
          Expanded(
            child: rawQueue.isEmpty
                ? ListView(
                    children: [
                      SizedBox(
                        height: MediaQuery.of(context).size.height * 0.5,
                        child: Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                padding: const EdgeInsets.all(18),
                                decoration: BoxDecoration(
                                  color:
                                      AppConfig.primaryColor.withAlpha(25),
                                  shape: BoxShape.circle,
                                ),
                                child: const Icon(
                                  Icons.assignment_turned_in_outlined,
                                  size: 48,
                                  color: AppConfig.primaryColor,
                                ),
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'All Reviews Completed!',
                                style: TextStyle(
                                  color: context.textPrimary,
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                'No appraisals are currently pending your approval.',
                                style: TextStyle(
                                    color: context.textSecondary,
                                    fontSize: 13),
                              ),
                              const SizedBox(height: 16),
                              TextButton.icon(
                                onPressed: () =>
                                    _tabController.animateTo(1),
                                icon: const Icon(Icons.history,
                                    color: AppConfig.primaryColor),
                                label: const Text('View Review History',
                                    style: TextStyle(
                                        color: AppConfig.primaryColor,
                                        fontWeight: FontWeight.bold)),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  )
                : filteredQueue.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.filter_list_off,
                                size: 40, color: context.textSecondary),
                            const SizedBox(height: 12),
                            Text('No items match your filter',
                                style: TextStyle(
                                    color: context.textPrimary,
                                    fontSize: 15,
                                    fontWeight: FontWeight.bold)),
                            const SizedBox(height: 12),
                            TextButton(
                              onPressed: () => setState(() {
                                _searchController.clear();
                                _selectedFilter = 'ALL';
                              }),
                              child: const Text('Clear Filters'),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 16, vertical: 12),
                        itemCount: filteredQueue.length,
                        itemBuilder: (context, index) =>
                            _buildQueueCard(context, filteredQueue[index],
                                reviewerProvider),
                      ),
          ),
        ],
      ),
    );
  }

  // ── Tab 2: Review History ────────────────────────────────────────────────────

  Widget _buildHistoryTab(ReviewerProvider reviewerProvider) {
    if (reviewerProvider.isHistoryLoading) {
      return const Center(
          child: SpinKitFadingCube(color: AppConfig.primaryColor, size: 40));
    }

    final history = reviewerProvider.history;

    return RefreshIndicator(
      onRefresh: () => reviewerProvider.fetchHistory(),
      child: history.isEmpty
          ? ListView(
              children: [
                SizedBox(
                  height: MediaQuery.of(context).size.height * 0.5,
                  child: Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.history_outlined,
                            size: 48,
                            color: context.textSecondary.withAlpha(120)),
                        const SizedBox(height: 12),
                        Text(
                          'No review history yet',
                          style: TextStyle(
                              color: context.textPrimary,
                              fontSize: 16,
                              fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Approved or returned appraisals will appear here.',
                          style: TextStyle(
                              color: context.textSecondary, fontSize: 13),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            )
          : ListView.builder(
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              itemCount: history.length,
              itemBuilder: (context, index) =>
                  _buildHistoryCard(context, history[index]),
            ),
    );
  }

  // ── History Card (read-only) ─────────────────────────────────────────────────

  Widget _buildHistoryCard(BuildContext context, ReviewQueueItem item) {
    final appraisal = item.appraisal;
    final wasApproved = item.actionedStatus == 'APPROVED';

    String formattedDate = '';
    if (item.actionedAt != null) {
      try {
        final dt = DateTime.parse(item.actionedAt!).toLocal();
        formattedDate =
            '${dt.day.toString().padLeft(2, '0')}/${dt.month.toString().padLeft(2, '0')}/${dt.year}';
      } catch (_) {}
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: context.textSecondary.withAlpha(25)),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withAlpha(context.isDarkMode ? 30 : 8),
              blurRadius: 8,
              offset: const Offset(0, 3))
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () {
            // Open appraisal in read-only detail view
            Provider.of<AppraisalProvider>(context, listen: false)
                .fetchAppraisalDetail(appraisal.id);
            Navigator.pushNamed(context, '/appraisal_detail',
                arguments: appraisal.id);
          },
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Staff info row
                Row(
                  children: [
                    CircleAvatar(
                      radius: 20,
                      backgroundColor: AppConfig.secondaryColor,
                      backgroundImage: (appraisal.staffProfilePictureUrl !=
                                  null &&
                              appraisal.staffProfilePictureUrl!.isNotEmpty)
                          ? NetworkImage(appraisal.staffProfilePictureUrl!)
                          : null,
                      child: (appraisal.staffProfilePictureUrl == null ||
                              appraisal.staffProfilePictureUrl!.isEmpty)
                          ? Text(
                              appraisal.staffName.isNotEmpty
                                  ? appraisal.staffName[0].toUpperCase()
                                  : 'S',
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold))
                          : null,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            appraisal.staffName,
                            style: TextStyle(
                                color: context.textPrimary,
                                fontSize: 15,
                                fontWeight: FontWeight.bold),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${appraisal.departmentName ?? 'Department'} • Staff ID: ${appraisal.staffId}',
                            style: TextStyle(
                                color: context.textSecondary, fontSize: 11),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    // Actioned badge
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: wasApproved
                            ? AppConfig.accentColor.withAlpha(30)
                            : AppConfig.warningColor.withAlpha(30),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        wasApproved ? 'Approved' : 'Returned',
                        style: TextStyle(
                          color: wasApproved
                              ? AppConfig.accentColor
                              : AppConfig.warningColor,
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 6),
                // Cycle name
                Text(
                  appraisal.cycleName,
                  style: TextStyle(
                      color: context.textSecondary,
                      fontSize: 11,
                      fontStyle: FontStyle.italic),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),

                const SizedBox(height: 6),
                // Clear Step Tag
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppConfig.primaryColor.withAlpha(20),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    'Step ${item.stepNumber}: ${item.stepLabel}',
                    style: const TextStyle(
                      color: AppConfig.primaryColor,
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),

                if (formattedDate.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Icon(Icons.schedule_outlined,
                          size: 13, color: context.textSecondary),
                      const SizedBox(width: 4),
                      Text(
                        'Actioned on $formattedDate',
                        style: TextStyle(
                            color: context.textSecondary, fontSize: 12),
                      ),
                    ],
                  ),
                ],

                // Comments preview
                if (item.comments != null && item.comments!.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: context.surfaceColor.withAlpha(80),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '"${item.comments}"',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: context.textSecondary,
                        fontSize: 12,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ),
                ],

                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        appraisal.cycleName,
                        overflow: TextOverflow.ellipsis,
                        maxLines: 1,
                        style: TextStyle(
                            color: context.textSecondary, fontSize: 11),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Row(
                      children: [
                        Icon(Icons.visibility_outlined,
                            size: 13, color: AppConfig.primaryColor),
                        const SizedBox(width: 4),
                        const Text('View (Read-only)',
                            style: TextStyle(
                                color: AppConfig.primaryColor,
                                fontSize: 12,
                                fontWeight: FontWeight.bold)),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ── Pending Queue Card ───────────────────────────────────────────────────────

  Widget _buildFilterChip(String value, String label) {
    final isSelected = _selectedFilter == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) setState(() => _selectedFilter = value);
      },
      selectedColor: AppConfig.primaryColor,
      backgroundColor: context.surfaceColor.withAlpha(100),
      labelStyle: TextStyle(
        color: isSelected ? Colors.white : context.textSecondary,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
        fontSize: 12,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      visualDensity: VisualDensity.compact,
    );
  }

  Widget _buildQueueCard(
    BuildContext context,
    ReviewQueueItem item,
    ReviewerProvider reviewerProvider,
  ) {
    final appraisal = item.appraisal;
    final bool isReturned = appraisal.status == 'RETURNED_TO_REVIEWER';

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isReturned
              ? AppConfig.warningColor.withAlpha(140)
              : context.textSecondary.withAlpha(30),
          width: isReturned ? 1.5 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withAlpha(context.isDarkMode ? 40 : 10),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(18),
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: () async {
            await Navigator.pushNamed(context, '/step_review', arguments: item);
            if (context.mounted) reviewerProvider.fetchQueue();
          },
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      radius: 22,
                      backgroundColor: AppConfig.primaryColor,
                      backgroundImage: (appraisal.staffProfilePictureUrl !=
                                  null &&
                              appraisal.staffProfilePictureUrl!.isNotEmpty)
                          ? NetworkImage(appraisal.staffProfilePictureUrl!)
                          : null,
                      child: (appraisal.staffProfilePictureUrl == null ||
                              appraisal.staffProfilePictureUrl!.isEmpty)
                          ? Text(
                              appraisal.staffName.isNotEmpty
                                  ? appraisal.staffName[0].toUpperCase()
                                  : 'S',
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 18))
                          : null,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            appraisal.staffName,
                            style: TextStyle(
                                color: context.textPrimary,
                                fontSize: 17,
                                fontWeight: FontWeight.bold),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${appraisal.departmentName ?? 'Department'} • ${appraisal.staffId}',
                            style: TextStyle(
                                color: context.textSecondary, fontSize: 12),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                // Cycle name
                Text(
                  appraisal.cycleName,
                  style: TextStyle(
                      color: context.textSecondary,
                      fontSize: 11,
                      fontStyle: FontStyle.italic),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 10),
                const SizedBox(height: 10),
                // Status Badge Row
                Align(
                  alignment: Alignment.centerLeft,
                  child: StatusBadge(
                    status: appraisal.status,
                    displayLabel: appraisal.statusDisplay,
                  ),
                ),
                const SizedBox(height: 6),
                // Green Step Badge Row
                Align(
                  alignment: Alignment.centerLeft,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(
                      color: AppConfig.primaryColor.withAlpha(25),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppConfig.primaryColor.withAlpha(50)),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.check_circle_outline_rounded, size: 12, color: AppConfig.primaryColor),
                        const SizedBox(width: 5),
                        Text(
                          'Step ${item.stepNumber}: ${item.stepLabel}',
                          style: const TextStyle(
                              color: AppConfig.primaryColor,
                              fontSize: 11,
                              fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Row(
                        children: [
                          Icon(Icons.calendar_today_outlined,
                              size: 14, color: context.textSecondary),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              appraisal.cycleName,
                              overflow: TextOverflow.ellipsis,
                              maxLines: 1,
                              style: TextStyle(
                                  color: context.textSecondary, fontSize: 12),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 8),
                      decoration: BoxDecoration(
                        gradient: AppConfig.primaryGradient,
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: [
                          BoxShadow(
                              color: AppConfig.primaryColor.withAlpha(60),
                              blurRadius: 6,
                              offset: const Offset(0, 2))
                        ],
                      ),
                      child: const Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text('Review',
                              style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13)),
                          SizedBox(width: 4),
                          Icon(Icons.arrow_forward,
                              color: Colors.white, size: 14),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
